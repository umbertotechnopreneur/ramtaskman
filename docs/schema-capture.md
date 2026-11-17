# ramtaskman capture format v1

We develop and test ramtaskman on Linux and Windows. The macOS backend is
experimental: we don't have a Mac, so we haven't tested or validated it.
Our own testing and CI cover Linux and Windows.

The `.rtm.json` format saves process-region **metadata** for local offline viewing.
It is independent of `--json`, which retains its previous contract. Files do not
contain application memory bytes, but can contain process names, paths, addresses,
PIDs and timestamps: treat them as potentially personal data. Captures are never
sent automatically.

## Container

The file is UTF-8 JSON. The root contains exactly these required fields:

| Field | Type | Meaning |
|---|---|---|
| `format` | string | `ramtaskman.capture` |
| `schema_version` | integer | `1` |
| `producer_version` | string | App version that wrote the file |
| `current_capture_id` | string | Identifier of current sample B |
| `baseline_capture_id` | string or null | Identifier of pinned sample A |
| `captures` | array | One or two capture records |

With one record, `baseline_capture_id` is null and `current_capture_id` refers to
that record. With two records, the two IDs must differ and each refer to a record.
Record order and timestamps do not determine roles. The v1 reader rejects unknown
versions or fields: it does not ignore extensions that could change number semantics.

## Capture record

All fields below are required, including when their value is null:

| Field | Type | Meaning |
|---|---|---|
| `capture_id`, `collection_session_id` | nonempty strings | Capture and collection-session identities |
| `sequence` | integer >= 0 | Request order within the session |
| `platform`, `backend_id`, `backend_version` | nonempty strings | Provider origin and contract |
| `pid` | positive integer | PID at collection time |
| `started_at` | finite number >= 0 | Process creation time, Unix seconds |
| `name` | nonempty string | Observed process name |
| `executable_identity` | string or null | Available executable identity; not opened during replay |
| `taken` | finite number >= 0 | Sample time, Unix seconds |
| `sample_ms` | finite number >= 0 | Collection duration in milliseconds |
| `complete` | boolean | Complete versus partial/failed region enumeration |
| `reason` | string or null | Main reason for incompleteness or failure |
| `metric_definitions` | string→string object | Counter definition identifiers |
| `capabilities` | string→boolean object | Declared provider capabilities |
| `metric_coverage` | string→integer-pair object | Measured count and observed region count |
| `issues` | array of strings | Reasons or notes associated with the sample |
| `regions` | array | Ordered list of observed regions |

Coverage uses **observed** regions as the denominator, even in a partial sample.
`complete=false` does not imply missing regions disappeared. `started_at` and
`taken` are Unix seconds; `sample_ms` is a duration, not a guarantee of atomicity.

Two captures can be compared over time only when session, process identity,
platform and required semantics are compatible. The same PID in two files does
not prove that they came from the same process.

## Region

Every field is required:

| Field | Type | Meaning |
|---|---|---|
| `start`, `end`, `offset` | strings | Canonical lowercase hexadecimal with `0x` prefix, no redundant leading zeros |
| `permissions`, `device`, `path`, `category` | strings | Range metadata and descriptive category |
| `inode` | integer >= 0 | File identifier reported by the provider where applicable |
| `rss`, `pss`, `uss`, `swap`, `swap_pss` | integer >= 0 or null | Byte counters; null means unavailable |
| `breakdown` | object mapping strings to integers or null | Additional counters in bytes |
| `vm_flags` | array of strings | Region attributes reported by the provider |

Ranges `[start, end)` are ascending, nonempty and non-overlapping. `end` and
`start` describe virtual space; virtual size is `end - start`, not necessarily
resident RAM. Region type describes the origin identified by the provider; it
does not prove what every page contains.

`0` is a measured zero; `null` is unknown or unsupported. PSS, USS, RSS and swap
are different views and must not be added indiscriminately.

## Validation and limits

The reader limits files to 64 MiB, captures to two, and regions to 32,768 per
capture. The read limit applies to actual bytes read. It rejects invalid JSON,
duplicate keys, NaN/Infinity, booleans in numeric positions, negative integers or
integers above unsigned 64-bit range, noncanonical/out-of-range addresses, strings
longer than 65,536 characters, C0/C1 control characters, isolated surrogates,
arrays/objects beyond internal limits, overlapping regions, inconsistent IDs and
coverage incompatible with observed regions. The sample timestamp must be
representable on the system displaying the file. Text is data and is never used as commands.

Writing uses a temporary file in the same directory, flush and fsync. An existing
path is not replaced without an explicit choice. If writing fails, the previous
file stays intact and the request's temporary file is removed. On filesystems
without hard-link support, creating without replacement can fail with the
corresponding error; choose a supported destination.

## Replay and comparison

```text
ramtaskman --language en --open capture.rtm.json
ramtaskman --language en --compare before.rtm.json after.rtm.json
```

`--open` opens one or two samples with the roles recorded in the file. `--compare`
accepts one sample per file: the first is A, the second B. Open files containing
two captures with `--open` instead. Replay creates neither a collector nor a
provider; pressing `r` does not resume live reads against the saved PID.

To reproduce a comparison, pin A in the region view, refresh the process to obtain
B, explicitly save the file, close the view and reopen the file. Values and A/B
semantics are the same; results remain sequential observations, and growth alone
does not prove a memory leak. If A and B are the same sample, the codec rejects
two records with the same ID: refresh B or remove the baseline and save only the
current sample.

The file contains the entire available sample, not just rows selected by filters.
View state (search, sorting and zoom) is not saved in version 1.
