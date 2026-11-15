# Câu trả lời mẫu UniStudy AI V3

Bộ đáp án dùng hai học phần Toán rời rạc và Thu thập và phân tích yêu cầu. Đối chiếu theo số trang vật lý của PDF, bắt đầu từ 1. Các câu hỏi dưới đây khớp với câu gợi ý trên giao diện V3.

## Toán rời rạc

### 1. Mệnh đề là gì?

Mệnh đề là một câu khẳng định có giá trị chân lý xác định, đúng hoặc sai. Ví dụ, “1 + 1 = 2” là mệnh đề đúng. “Bây giờ là mấy giờ?” là câu hỏi nên không có giá trị đúng hoặc sai.

**Nguồn** — chuong 1-logic menh de_2025.pdf, trang 4.

### 2. Tập hợp là gì?

Tập hợp hình thành bằng cách nhóm các đối tượng. Mỗi đối tượng trong nhóm gọi là một phần tử. Ký hiệu x ∈ A nghĩa là x thuộc tập A. Tập rỗng, ký hiệu ∅ hoặc {}, là tập không chứa phần tử nào.

**Nguồn** — Chuong 2 - Tap hop - 2020.pdf, trang 2.

### 3. Phép hợp và phép giao là gì?

Hợp A ∪ B gồm các phần tử thuộc ít nhất một trong hai tập A và B. Giao A ∩ B gồm các phần tử thuộc cả A và B. Hai tập rời nhau khi giao của chúng là tập rỗng.

**Nguồn** — Chuong 2 - Tap hop - 2020.pdf, trang 9.

### 4. Đường một nét Euler là gì?

Trong đồ thị vô hướng, đường một nét Euler là hành trình đi qua mọi cạnh đúng một lần. Nếu đỉnh đầu trùng đỉnh cuối thì đường Euler khép kín. Nếu hai đỉnh khác nhau thì đường Euler mở.

**Nguồn** — Chuong 6. Ly thuyet do thi - P2.pdf, trang 21.

## Thu thập và phân tích yêu cầu

### 5. Yêu cầu chức năng khác yêu cầu phi chức năng như thế nào?

Yêu cầu chức năng mô tả chức năng hoặc dịch vụ hệ thống phải cung cấp. Yêu cầu phi chức năng quy định các đặc tính hoặc ràng buộc, chẳng hạn độ tin cậy, thời gian phản ứng và dung lượng lưu trữ. Một cách phân biệt là hỏi hệ thống phải làm việc gì và việc đó phải đáp ứng điều kiện nào.

**Nguồn** — Chapter 1 Gioi thieu chung_Long.pdf, trang 22 và 30. Trang 34 có ví dụ yêu cầu phi chức năng kiểm định được.

### 6. Các kỹ thuật phổ biến để khám phá yêu cầu phần mềm?

Giáo trình chia thành năm nhóm gồm điều tra, sáng tạo, lấy tài liệu làm trung tâm, quan sát và hỗ trợ. Ví dụ, phỏng vấn và phiếu điều tra thuộc nhóm điều tra. Khảo sát và đọc tài liệu hiện có thuộc nhóm lấy tài liệu làm trung tâm.

**Nguồn** — Chapter 3 Kham pha yeu cau_Long.pdf, trang 29–34. Trang 29 liệt kê năm nhóm.

### 7. Biểu đồ Use Case dùng để mô hình hóa khía cạnh nào của hệ thống?

Biểu đồ ca sử dụng mô tả các chức năng của hệ thống từ góc nhìn người dùng và mối quan hệ của chúng với môi trường bên ngoài. Biểu đồ cho thấy hệ thống sẽ được sử dụng như thế nào.

**Nguồn** — Chuong 6 Tai lieu hoa yeu cau bang mo hinh_Long.pdf, trang 15.

### 8. Tại sao cần tài liệu hóa yêu cầu bằng ngôn ngữ tự nhiên rõ ràng?

Ngôn ngữ tự nhiên giúp các bên liên quan đọc và hiểu yêu cầu mà ít cần chuẩn bị trước. Cách diễn đạt rõ ràng giúp giảm nguy cơ mỗi người hiểu câu chữ theo kinh nghiệm riêng, làm sai lệch thông tin khi truyền đạt hoặc triển khai.

**Nguồn** — Chuong 5 Tai lieu hoa yeu cau bang ngon ngu tu nhien_Long.pdf, trang 2 và 4. Tra cứu trả trang 2 trước.

## Tám tình huống kiểm tra V3

| Ca | Nhóm | Đầu vào và điều kiện | Mong đợi | Quan sát |
|---|---|---|---|---|
| TH01 | Bình thường | Toán rời rạc, tra cứu “Tập hợp là gì?” | Định nghĩa và trang nguồn | Trả định nghĩa từ trang 2 chương Tập hợp |
| TH02 | Bình thường | Thu thập và phân tích yêu cầu, tra cứu câu hỏi so sánh hai loại yêu cầu | Có căn cứ cho cả hai loại | Trả các trang 22, 30 và 34 chương Giới thiệu chung |
| TH03 | Thiếu thông tin | Hội thoại mới, “Cho ví dụ?” | Hỏi lại chủ đề | needs_clarification, không có nguồn |
| TH04 | Thiếu thông tin | Hội thoại mới, “Hãy nói rõ phần này.” | Hỏi lại phần cần giải thích | needs_clarification, không có nguồn |
| TH05 | Ngoài phạm vi | Toán rời rạc, hỏi ngày bắt đầu đăng ký học phần kỳ tới, chọn Qwen | Báo thiếu căn cứ trước khi gọi mô hình | insufficient_evidence, không có câu trả lời hay nguồn |
| TH06 | Ngoài phạm vi | Toán rời rạc, hỏi biểu đồ Use Case, chọn Qwen | Báo thiếu căn cứ trong PDF Toán rời rạc | insufficient_evidence, không có câu trả lời hay nguồn |
| TH07 | Lỗi công cụ | Câu hỏi TH01, chọn qwen3.5:4b chưa được cài | Báo tên mô hình thiếu, giữ nguồn tra cứu | ai_unavailable, thông báo đúng qwen3.5:4b và vẫn có nguồn |
| TH08 | Lỗi công cụ | Tạm làm mất bản sao PDF Tập hợp sau khi lập danh mục | 404 khi thiếu PDF, 200 sau khi khôi phục | API ảnh trang 2 trả 200 → 404 → 200. Lỗi được tạo trên bản sao tạm |

**Kiểm tra Ollama thật.** Với tám câu gợi ý, qwen2.5:1.5b trả bảy phản hồi sinh nội dung và một lỗi định dạng ở câu về ngôn ngữ tự nhiên. Câu Mệnh đề và câu Use Case có ý chính khớp trang dẫn. Một số câu vẫn sai hoặc thiếu ý, ví dụ đảo phép hợp với phép giao, gọi phần tử là dấu thập phân, hoặc chỉ nêu một trong năm nhóm kỹ thuật khám phá yêu cầu. Trên giao diện, bấm gợi ý Tập hợp đã gửi đúng mô hình và nhận mode ai. Dùng đáp án và trang nguồn trong tài liệu này làm chuẩn chấm nội dung.

**Kiểm tra thêm.** Câu hỏi thủ đô Nhật Bản trong Toán rời rạc và câu hỏi thời tiết trong Thu thập và phân tích yêu cầu đều trả insufficient_evidence. Đầu vào trống trả HTTP 422. Bộ kiểm thử Python chạy 112 ca thành công.
