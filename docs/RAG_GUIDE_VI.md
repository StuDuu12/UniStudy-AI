# Kiểm tra tra cứu PDF trong UniStudy AI

Khi nạp PDF, ứng dụng trích văn bản từng trang và chia thành các đoạn tối đa 135 từ, chồng lấp 25 từ. Mỗi đoạn giữ mã tài liệu, tên tệp, số trang PDF và dấu vân tay của tệp. Số trang PDF đếm từ 1 theo thứ tự vật lý trong tệp.

Hệ thống chuẩn hóa câu hỏi tiếng Việt và dùng TF-IDF để xếp hạng các đoạn trong học phần đang chọn. Câu hỏi nhiều ý có thể nhận thêm nguồn cho từng ý. Khi có đoạn liền kề giúp đọc trọn ngữ cảnh, hệ thống có thể đưa cả đoạn đó vào kết quả. Ngưỡng điểm 0,20 áp dụng cho các đoạn tìm trực tiếp. Điểm xếp hạng phản ánh độ khớp từ khóa.

Khi có cấu hình AI, backend gửi câu hỏi và các đoạn đã chọn đến endpoint tương thích Chat Completions trong `.env`. Với dịch vụ từ xa, các đoạn từ PDF tải lên được gửi khi khớp trực tiếp với câu hỏi. Backend chỉ chấp nhận các mã nguồn đã gửi và dùng chúng để tra ra tên tệp, số trang và đoạn trích. Khi AI báo thiếu căn cứ hoặc không phản hồi, giao diện hiển thị trạng thái và các đoạn PDF tìm được. Khi chưa cấu hình AI, ứng dụng trả về đoạn tra cứu từ PDF.

## Xem các đoạn được chọn

Chạy từ thư mục gốc dự án.

```powershell
# Liệt kê mã học phần và số PDF
.\.venv\Scripts\python.exe -m backend.rag_inspect

# Xem các đoạn mà ứng dụng chọn cho một câu hỏi mới
.\.venv\Scripts\python.exe -m backend.rag_inspect --course toan_roi_rac --question "Tập hợp là gì?"

# Giới hạn ở ba đoạn tìm trực tiếp
.\.venv\Scripts\python.exe -m backend.rag_inspect --course toan_roi_rac --question "Tập hợp là gì?" --top-k 3
```

Lệnh trả về tên tệp, trang PDF, đoạn trích và điểm khớp. Mở trang trong ứng dụng để đối chiếu công thức, bảng hoặc các ký hiệu có thể bị lỗi khi trích văn bản.

## Chạy bộ câu hỏi phát triển

```powershell
.\.venv\Scripts\python.exe -m backend.evaluate_rag
.\.venv\Scripts\python.exe -m pytest backend/tests tests -q
```

Lệnh đánh giá dùng học liệu Toán rời rạc và in trạng thái cùng số trang tìm được cho từng câu. Thêm `--output` kèm đường dẫn để lưu báo cáo JSON có đoạn trích. Thêm `--live` khi muốn kiểm tra dịch vụ AI đã cấu hình bằng bộ câu hỏi đó.
