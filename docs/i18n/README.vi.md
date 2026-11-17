# ramtaskman

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Hiểu RAM đang được dùng vào đâu, ngay trong terminal.

ramtaskman là trình theo dõi bộ nhớ thử nghiệm, được phát triển và kiểm thử trên Linux và Windows. Dự án xuất phát từ sự tò mò và nghiên cứu: hiểu bộ nhớ trên nhiều hệ thống mà không cần những công cụ quá phức tạp. Đây là một dự án [VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto).

Dự án cũng có backend macOS thử nghiệm. Chúng tôi không có máy Mac nên chưa kiểm thử hay xác nhận khả năng hoạt động của backend này. Các bài kiểm thử và CI của dự án chỉ chạy trên Linux và Windows.

[Tài liệu](../README.md) · [Đóng góp](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman](../images/cover.png)

*Giao diện Textual thực được chụp trên Linux với dữ liệu giả lập. Ảnh bìa trích phần tổng quan và bảng; giao diện minh họa dùng tiếng Anh.*

## Bắt đầu

Cần Python 3.11 trở lên và uv. Linux cần /proc và smaps_rollup. Lần chạy đầu cần mạng để cài các phụ thuộc đã khóa. Môi trường và bộ nhớ đệm nằm trong thư mục dự án.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

Trên Windows, mở Windows Terminal tại thư mục dự án:

```powershell
.\run.cmd
```

Dùng --once để lấy một mẫu hoặc --json để xuất JSON. Không dùng chung .venv giữa các hệ điều hành; hãy tạo lại cục bộ. Dự án chưa được phát hành trên PyPI.

Phím hữu ích: m đổi chế độ, g đổi ứng dụng/tiến trình, / tìm kiếm, f lọc, d xem chi tiết, r mở vùng nhớ, ? giải thích chỉ số và q thoát. Hướng dẫn kỹ thuật đầy đủ hiện bằng tiếng Anh.

Chạy bảng điều khiển bằng `./run.sh --language vi` (Windows: `.\run.cmd --language vi`). Văn bản của ứng dụng hiện có bằng mười ngôn ngữ: `--language` chọn ngôn ngữ cho giao diện, chân trang, trợ giúp, CLI và báo cáo văn bản `--once`. Các thông báo kỹ thuật do ứng dụng tạo ra cũng đã được dịch. Định danh và cấu trúc JSON được giữ ổn định; chi tiết từ hệ điều hành và văn bản trong các bản ghi đã lưu vẫn giữ ngôn ngữ gốc. Phạm vi xác minh cục bộ là Linux với Python 3.14.4: giao diện dữ liệu tổng hợp ở 160×48 và 80×24, CLI, dựng gói, cài đặt biệt lập và phát lại. Windows được kiểm tra qua CI; macOS không thuộc phạm vi xác minh của dự án. Các bản dịch vẫn cần người bản ngữ rà soát.

## Các chức năng chính

1. Xem RAM hệ thống, bộ nhớ khả dụng, bộ nhớ đệm và biểu đồ lịch sử; chọn chế độ Slim hoặc chẩn đoán đầy đủ.
2. Khám phá ứng dụng và tiến trình, sắp xếp theo chỉ số có sẵn và kiểm tra độ bao phủ của phép đo.
3. Xem RSS và USS; trên Linux còn có PSS, swap và SwapPSS, với dữ liệu thiếu được chỉ rõ.
4. Tìm theo tên, tệp thực thi hoặc PID chính xác; lọc theo người dùng, swap hay dữ liệu chưa đầy đủ.
5. Khám phá vùng nhớ tiến trình trên Linux; chế độ địa chỉ ảo Windows còn thử nghiệm.
6. So sánh hai mẫu, lưu và mở lại bản ghi cục bộ, kể cả khi ngoại tuyến.

## Xem bên trong

![Full diagnostics](../images/full-diagnostics.png)

[Thư viện hình ảnh](../images/README.md) · [A/B](../images/regions-comparison.png) · [10 languages](../images/multilingual.png)

## Giá trị RAM và phân bổ theo tháng

```bash
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
```

Bạn tự nhập giá toàn bộ RAM; ứng dụng không tra giá hay gửi yêu cầu mạng. Dung lượng mặc định là phần hệ điều hành nhìn thấy; dùng `--ram-capacity-gib 32` cho bộ RAM danh nghĩa 32 GiB. Giá trị = giá × số byte phân bổ được / dung lượng. `--ram-months` chia giá trị phần cứng này cho số tháng đã chọn: đây không phải hóa đơn, điện năng, trung bình tháng hay khoản tiết kiệm bảo đảm. Linux dùng PSS; Windows dùng USS, chỉ tính bộ nhớ riêng đang thường trú. Không thay bằng RSS. Nhóm thiếu dữ liệu vẫn là n/a (`null` trong JSON). Không cộng ứng dụng với các tiến trình thành viên hoặc bộ nhớ hệ thống. Các mẫu được lấy tuần tự, không đồng thời. JSON chỉ thêm `ram_valuation` khi được yêu cầu. F1 mở thông tin và ghi công; Esc quay lại màn hình theo dõi.

## Dự án thử nghiệm: hãy đọc số liệu cẩn thận

Các phép đọc diễn ra tuần tự, quyền truy cập có thể hạn chế khả năng quan sát và việc nhóm ứng dụng chỉ là phương pháp phỏng đoán. Dữ liệu thiếu là n/a, không phải số không. RSS có thể đếm trùng trang chia sẻ; PSS của tiến trình không phải tổng RAM. Bộ nhớ đệm chồng lấp với bộ nhớ khả dụng. Swap của tiến trình không được suy ra từ commit.

Linux cung cấp PSS và swap theo tiến trình khi có thể đọc. Ở đây Windows và backend macOS thử nghiệm không cung cấp các chỉ số này. Vùng nhớ Linux dùng smaps; Windows chỉ có khoảng địa chỉ ảo thử nghiệm; macOS chưa có bản đồ. Việc xác minh của dự án gồm kiểm tra Linux cục bộ và kiểm tra Windows gốc qua CI; macOS vẫn nằm ngoài phạm vi đó.

Việc kiểm tra thủ công trên PC Windows cá nhân vẫn chưa được thực hiện.

## Sử dụng, chỉnh sửa, chia sẻ

Bạn có thể sử dụng, sao chép, chỉnh sửa và phân phối lại ramtaskman, kể cả thương mại, theo [giấy phép MIT](../../LICENSE). Giữ thông báo bản quyền và cấp phép trong các bản sao hoặc phần đáng kể. Phần mềm được cung cấp không có bảo hành. Hoan nghênh đóng góp và sửa bản dịch; các thư viện phụ thuộc giữ giấy phép riêng.

[Đóng góp](../../CONTRIBUTING.md) · [Ghi công bên thứ ba](../../THIRD_PARTY_NOTICES.md)

## Cảm hứng và lời cảm ơn

Xin cảm ơn Scott Hanselman và GPU Taskman vì nguồn cảm hứng. ramtaskman tái sử dụng một phần dự án và điều chỉnh giao diện terminal cho RAM; đây là dự án độc lập, không phải bản phát hành chính thức. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Bản dịch được thực hiện với sự hỗ trợ của AI. Rất hoan nghênh góp ý từ dịch giả và người bản ngữ.

[Hướng dẫn kỹ thuật đầy đủ (tiếng Anh)](../guida.md) · [Giấy phép MIT; giữ nguyên bản quyền gốc.](../../LICENSE)
