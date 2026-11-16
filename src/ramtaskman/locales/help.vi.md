# ramtaskman · cách đọc các con số

Chúng tôi phát triển và kiểm thử trên Linux và Windows. Backend macOS mang tính thử nghiệm, chưa được dự án kiểm thử hoặc xác minh vì chúng tôi không có máy Mac. Mọi hoạt động xác minh macOS đều phụ thuộc vào đóng góp bên ngoài; CI của dự án không bao gồm macOS.

Cấu trúc giao diện của gputaskman, được điều chỉnh cho bộ nhớ trên Linux, Windows và macOS.

| Trường | Ý nghĩa |
|---|---|
| PSS | RAM riêng cộng phần được phân bổ theo tỷ lệ của các trang chia sẻ |
| USS | Private_Clean + Private_Dirty: các trang cư trú riêng |
| RSS | Các trang cư trú, kể cả trang chia sẻ; cộng lại có thể đếm trùng |
| Swap | Swap từ smaps_rollup, không gồm swap shmem; có thể đếm trùng trang chia sẻ |
| SwapPSS | Phần theo tỷ lệ của swap chia sẻ được smaps_rollup ghi nhận |
| RAM used | MemTotal − MemAvailable; không phải tổng của các tiến trình |
| Cache | Cached + Buffers + SReclaimable − Shmem; chồng lấp với bộ nhớ khả dụng |
| PSI some | Phần trăm thời gian có ít nhất một tác vụ chờ bộ nhớ, trung bình 10 giây |

**Thanh RAM:** dùng toàn bộ chiều rộng và chia các bộ đếm Linux thành bộ nhớ ẩn danh, bộ nhớ đệm tệp (Cached − Shmem), chia sẻ/tmpfs, bộ đệm, slab có thể/không thể thu hồi, khác (phần dư được tính) và trống. Đây là các nhóm kế toán; thứ tự không biểu thị địa chỉ vật lý. Bộ nhớ khả dụng là chỉ số riêng, có cả bộ nhớ đệm có thể thu hồi, nên không phải phân đoạn bổ sung. Chi tiết clean/dirty và PSS của tiến trình nằm trong **d** vì chồng lấp với số liệu toàn cục. Nếu thiếu trường hoặc mẫu không nhất quán, thanh hiển thị đang dùng/khả dụng và nêu lý do không có phân bổ. Chú giải vẫn có các nhóm nhỏ hơn một ký tự.

**Thanh USS ứng dụng:** hiển thị 10 ứng dụng đầu có USS đầy đủ và các ứng dụng đầy đủ còn lại. Thang là tổng USS của các ứng dụng đầy đủ trong mẫu, không phải tổng RAM. Số và màu tương ứng với chú giải. Nhóm thiếu dữ liệu bị loại trừ và độ bao phủ được ghi rõ. Cách nhóm theo bảng; các phân đoạn không phải địa chỉ vật lý.

**Windows/macOS:** USS và RSS lấy từ psutil; PSS, Swap và SwapPSS theo tiến trình không được cung cấp và giữ n/a. Commit riêng/pagefile trên Windows KHÔNG phải swap trên đĩa. Trên macOS, RAM used là total − available của psutil, không phải Memory Pressure trong Activity Monitor.

**Ứng dụng:** trên Linux, cgroup systemd rõ ràng xác định phiên bản ứng dụng, kể cả các tiến trình phụ dùng tệp thực thi khác nhau. Người dùng và phiên bản khác nhau được tách riêng. Khi thiếu danh tính này, kể cả trên Windows/macOS, dùng người dùng + tệp thực thi, hoặc người dùng + tên như phương pháp phỏng đoán nếu không đọc được đường dẫn. Bảng kiểm tra nêu phương pháp.

**Tìm kiếm và bộ lọc:** **/** tìm tên, tệp thực thi hoặc PID chính xác; **f** chọn người dùng và trạng thái bộ nhớ (**có swap** hoặc **dữ liệu một phần**). Các bộ lọc kết hợp với nhau. Ứng dụng khớp khi một tiến trình khớp tìm kiếm hoặc trạng thái, nhưng tổng vẫn giữ mọi thành viên. Bộ lọc được giữ khi vào chế độ tiến trình. Chúng áp dụng trước giới hạn Top 30; biểu đồ và bảng điều khiển mô tả toàn hệ thống. **Enter** từ ô tìm kiếm quay về bảng. **Esc** trong điều khiển hoặc **Reset** xóa bộ lọc; **Esc** trong bảng tiến trình quay lại ứng dụng và giữ bộ lọc. Dữ liệu một phần chỉ xét bộ đếm được hệ thống hỗ trợ; swap chưa biết không đồng nghĩa đang dùng swap.

**d** mở chi tiết RAM của nhóm hoặc tiến trình: PSS ẩn danh/tệp/shmem, riêng và chia sẻ clean/dirty, trang ẩn danh, LazyFree và THP. Đây là các trường Linux; hệ thống khác là n/a. Các dòng là góc nhìn chồng lấp, không được cộng tất cả. Mẫu được cố định lúc mở; đóng và mở lại để cập nhật. **Esc** hoặc **d** đóng chi tiết.

**r** hoặc **Enter** trên tiến trình mở bản đồ vùng nhớ Linux. Trên ứng dụng, **r** hiển thị PID trước: mỗi tiến trình có không gian ảo riêng. Các thanh trong **d** chia PSS và RSS riêng biệt; swap nằm ngoài RAM cư trú.

Trong bản đồ, **v** đổi RSS/địa chỉ ảo, **s** sắp xếp, **/** tìm tệp hoặc địa chỉ 0x…, **f** lọc loại/trạng thái, **z** hoặc **Enter** phóng to vùng lân cận của vùng chọn, **r** làm mới và **Esc** xóa bộ lọc/thoát phóng to/quay lại. Bản đồ theo địa chỉ ảo, không phải khung trang vật lý. Khoảng trống bị loại khỏi thang ảo và đánh dấu bằng │; vùng nhỏ hơn một ký tự vẫn có trong bảng. Loại nói về nguồn gốc ánh xạ, không phải nội dung: tệp có thể chứa trang CoW riêng; chỉ heap/stack được nhận diện mới được gọi như vậy. Mẫu được đọc theo yêu cầu và nêu tuổi, thời lượng, giới hạn đọc. Windows chỉ có khoảng ảo thử nghiệm; macOS chưa có bản đồ vùng nhớ.

Trong vùng nhớ, **b** cố định A, **r** lấy B và **c** mở so sánh. Khi so sánh, **v** đổi chỉ số, **s** đổi thứ tự, **f** lọc trạng thái và **Ctrl+B** bỏ A. **Ctrl+S** lưu mẫu; **Ctrl+O** mở tệp ngoại tuyến. Tệp chứa siêu dữ liệu và có thể gồm đường dẫn cá nhân. Dữ liệu thiếu và vùng tái cấu trúc vẫn là n/a; cùng khoảng địa chỉ không chứng minh cùng một cấp phát hay rò rỉ bộ nhớ.

**n/a không phải số không.** Tổng ứng dụng là n/a nếu thiếu dù chỉ một giá trị. Lần đọc cho biết độ bao phủ PSS/USS. Tổng hiển thị chỉ là tổng một phần của các số liệu đọc được, không phải toàn bộ RAM hệ thống. Việc đọc không nguyên tử: tiến trình có thể thay đổi trong khi thu thập. Người dùng khác, sandbox và quyền procfs có thể ngăn đọc. Không tự động nâng quyền. HugeTLB không nằm trong các bộ đếm RSS/PSS/USS thông thường được hiển thị ở đây.

Chương trình đọc siêu dữ liệu, không đọc /proc/PID/mem, cmdline, environment hay nội dung ứng dụng.

**g** ứng dụng/tiến trình · **Enter** tiến trình của ứng dụng đã chọn · **Esc** về ứng dụng

**s** sắp xếp · **c** biểu đồ · **a** tất cả/30 đầu · **m** gọn/đầy đủ

**/** tìm kiếm · **f** bộ lọc · **d** chi tiết · **r** vùng nhớ · **p** tạm dừng · **?** trợ giúp · **q** thoát

Biểu đồ hiển thị 60 mẫu gần nhất, phần trăm trên thang 0–100. Khoảng trắng nghĩa là thiếu dữ liệu. Khoảng lấy mẫu là thời gian nghỉ sau phép đo; chu kỳ thực còn gồm thời gian quét.
