/* Diagnostic for this helper process only. Uses the installed macOS SDK ABI. */
#ifndef __APPLE__
#error "This diagnostic requires macOS and the native SDK"
#endif

#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/vm_region.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define MAX_CALLS 100000
#define MAX_DEPTH 32
#define TEST_BYTES (8u * 1024u * 1024u)

typedef struct {
    unsigned long leaves, submaps, calls;
    unsigned long long total_virtual;
    unsigned max_depth;
    int end_code, limited;
} walk_result;

/* Only inspect the process that owns the borrowed mach_task_self() port. */
static int query(mach_vm_address_t *address, mach_vm_size_t *size,
                 natural_t *depth, vm_region_submap_info_data_64_t *info) {
    mach_msg_type_number_t count = VM_REGION_SUBMAP_INFO_COUNT_64;
    memset(info, 0, sizeof(*info));
    kern_return_t kr = mach_vm_region_recurse(mach_task_self(), address, size,
        depth, (vm_region_recurse_info_t)info, &count);
    if (kr == KERN_SUCCESS && count < VM_REGION_SUBMAP_INFO_V0_COUNT_64) {
        return KERN_FAILURE;
    }
    return kr;
}

static walk_result walk(void) {
    walk_result result = {0};
    mach_vm_address_t address = 0;
    natural_t depth = 0;
    mach_vm_address_t previous_end = 0;
    while (result.calls < MAX_CALLS) {
        mach_vm_size_t size = 0;
        vm_region_submap_info_data_64_t info;
        int kr = query(&address, &size, &depth, &info);
        result.calls++;
        if (kr != KERN_SUCCESS) {
            result.end_code = kr;
            break;
        }
        if (!size || address > UINT64_MAX - size) {
            result.end_code = KERN_FAILURE;
            break;
        }
        if (depth > result.max_depth) result.max_depth = depth;
        if (info.is_submap) {
            result.submaps++;
            if (depth >= MAX_DEPTH) {
                result.limited = 1;
                break;
            }
            depth++;
        } else {
            if (address < previous_end) {
                result.end_code = KERN_FAILURE;
                break;
            }
            result.leaves++;
            if (result.total_virtual > UINT64_MAX - size) {
                result.end_code = KERN_FAILURE;
                break;
            }
            result.total_virtual += size;
            address += size;
            previous_end = address;
        }
    }
    if (result.calls >= MAX_CALLS) result.limited = 1;
    return result;
}

/* Query the one anonymous mapping created by this helper, without reading bytes. */
static int target(uintptr_t target_address, unsigned *resident_pages,
                  unsigned long long *region_size) {
    mach_vm_address_t address = (mach_vm_address_t)target_address;
    natural_t depth = 0;
    for (unsigned i = 0; i < MAX_DEPTH + 1; i++) {
        mach_vm_size_t size = 0;
        vm_region_submap_info_data_64_t info;
        int kr = query(&address, &size, &depth, &info);
        if (kr != KERN_SUCCESS) return kr;
        if (!size || address > target_address || size <= target_address - address) {
            return KERN_INVALID_ADDRESS;
        }
        if (!info.is_submap) {
            *resident_pages = info.pages_resident;
            *region_size = size;
            return KERN_SUCCESS;
        }
        if (depth >= MAX_DEPTH) return KERN_RESOURCE_SHORTAGE;
        depth++;
    }
    return KERN_RESOURCE_SHORTAGE;
}

int main(void) {
    long page = sysconf(_SC_PAGESIZE);
    if (page <= 0 || TEST_BYTES % (unsigned long)page != 0) {
        fprintf(stderr, "Dimensione pagina non valida o non supportata\n");
        return 2;
    }
    void *allocation = mmap(NULL, TEST_BYTES, PROT_READ | PROT_WRITE,
                            MAP_PRIVATE | MAP_ANON, -1, 0);
    if (allocation == MAP_FAILED) {
        fprintf(stderr, "mmap fallita: %s\n", strerror(errno));
        return 2;
    }
    unsigned before = 0, after = 0;
    unsigned long long region_before = 0, region_after = 0;
    int before_kr = target((uintptr_t)allocation, &before, &region_before);
    /* The only contents modified are the helper's synthetic anonymous pages. */
    volatile unsigned char *p = (volatile unsigned char *)allocation;
    for (size_t offset = 0; offset < TEST_BYTES; offset += (size_t)page) p[offset] = 1;
    int after_kr = target((uintptr_t)allocation, &after, &region_after);
    walk_result samples[3];
    struct rusage before_usage, after_usage;
    int usage_before_ok = getrusage(RUSAGE_SELF, &before_usage) == 0;
    clock_t start = clock();
    for (unsigned i = 0; i < 3; i++) samples[i] = walk();
    clock_t finish = clock();
    int usage_after_ok = getrusage(RUSAGE_SELF, &after_usage) == 0;
    int unmapped = munmap(allocation, TEST_BYTES) == 0;
    printf("{\"probe\":\"macos-self-region\",\"page_bytes\":%ld,"
           "\"allocation_bytes\":%u,\"before_kr\":%d,\"after_kr\":%d,"
           "\"before_resident_pages\":", page, TEST_BYTES, before_kr, after_kr);
    if (before_kr == KERN_SUCCESS) printf("%u", before); else printf("null");
    printf(",\"after_resident_pages\":");
    if (after_kr == KERN_SUCCESS) printf("%u", after); else printf("null");
    printf(",\"before_region_bytes\":");
    if (before_kr == KERN_SUCCESS) printf("%llu", region_before); else printf("null");
    printf(",\"after_region_bytes\":");
    if (after_kr == KERN_SUCCESS) printf("%llu", region_after); else printf("null");
    printf(",\"enumerations\":[");
    for (unsigned i = 0; i < 3; i++) {
        if (i) putchar(',');
        printf("{\"leaves\":%lu,\"submaps\":%lu,\"calls\":%lu,"
               "\"virtual_bytes\":%llu,\"max_depth\":%u,\"end_code\":%d,\"limited\":%s}",
               samples[i].leaves, samples[i].submaps, samples[i].calls,
               samples[i].total_virtual, samples[i].max_depth, samples[i].end_code,
               samples[i].limited ? "true" : "false");
    }
    printf("],\"cpu_seconds\":%.6f,\"rss_before_native\":", (double)(finish-start)/CLOCKS_PER_SEC);
    if (usage_before_ok) printf("%ld", before_usage.ru_maxrss); else printf("null");
    printf(",\"rss_after_native\":");
    if (usage_after_ok) printf("%ld", after_usage.ru_maxrss); else printf("null");
    printf(",\"munmap_ok\":%s}\n", unmapped ? "true" : "false");
    int walks_ok = 1;
    for (unsigned i = 0; i < 3; i++) {
        /* End conventions vary across Darwin versions; preserve the exact code. */
        if (samples[i].limited || !samples[i].leaves ||
            (samples[i].end_code != KERN_INVALID_ADDRESS && samples[i].end_code != KERN_NO_SPACE)) walks_ok = 0;
    }
    return before_kr == KERN_SUCCESS && after_kr == KERN_SUCCESS && unmapped && walks_ok ? 0 : 1;
}
