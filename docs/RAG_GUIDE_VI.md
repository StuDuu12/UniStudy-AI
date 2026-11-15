# Hiểu và kiểm tra RAG trong UniStudy AI

## 1. Dự án này đang làm gì?

Đọc code bản React/FastAPI theo thứ tự sau:

1. `backend/services/ingest.py`: PDF → văn bản từng trang → các đoạn (chunk).
2. `backend/services/retrieval.py`: biến đoạn và câu hỏi thành vector TF-IDF, tính cosine similarity, lấy top-k.
3. `backend/services/course_manager.py`: chỉ tìm trong học phần được chọn, lọc điểm, gọi AI nếu đã cấu hình.
4. `backend/services/llm_service.py`: gửi câu hỏi và các đoạn tới AI; chỉ chấp nhận ID nguồn được cung cấp.
5. `backend/routers/chat.py`: nhận câu hỏi từ giao diện qua `POST /api/chat`.
6. `frontend/src/components/sources/SourceCard.tsx`: hiển thị đoạn, tên PDF, trang và nút xem nguồn.

`src/schemas.py` và `services/` ở thư mục gốc chủ yếu phục vụ bản Streamlit cũ; backend vẫn tái sử dụng một số tiện ích upload và khóa đọc PDF trong đó. Luồng tạo câu trả lời React/FastAPI hiện dùng `backend/services/llm_service.py`.

```text
PDF → đọc từng trang → chia chunk → lưu metadata → lập chỉ mục theo học phần
                                                        ↓
Câu hỏi → vector hóa → xếp hạng → top 3 → lọc điểm ≥ 0.20
                                             ↓
                     Có cấu hình AI: AI đọc các đoạn, trả lời + ID nguồn
                     Chưa cấu hình AI: trích nguyên đoạn đầu để tra cứu
                                             ↓
                       Metadata thật → tên PDF + trang PDF + đoạn trích
```

**Chunk** là đoạn văn được tạo khi nạp PDF. **Top-k** là tối đa k đoạn được chọn khi có câu hỏi. Không phải chia PDF thành k đoạn, cũng không phải lấy k trang đầu của PDF.

Ví dụ câu hỏi “Phân vùng tương đương là gì?”: hệ thống xếp hạng tất cả chunk trong môn Kiểm thử phần mềm, rồi chọn tối đa 3 đoạn. Mỗi đoạn có thể nằm ở các trang khác nhau. AI chỉ nhận các đoạn vượt ngưỡng, không đọc toàn bộ PDF trong mỗi lượt hỏi.

## 2. Vì sao biết đúng trang?

Khi đọc PDF, chương trình đánh số trang vật lý từ 1. Mỗi chunk giữ `document_id`, `document_name`, `page`, `chunk_id`, `excerpt` và dấu vân tay `document_sha256`. Chunk tối đa 135 từ, chồng lấp 25 từ với chunk tiếp theo, và không ghép sang trang khác. Chồng lấp giúp giữ ngữ cảnh ở chỗ cắt, nhưng không đảm bảo luôn giữ trọn câu.

AI chỉ chọn các ID như `S1`, `S2`; backend ánh xạ chúng về metadata thật. ID lạ hoặc thiếu ID làm câu trả lời bị từ chối. Số trang PDF có thể khác số trang in trên slide. Nút xem trang dùng số trang PDF.

Đây là bảo đảm về xuất xứ đoạn trích. Nó chưa chứng minh đoạn được truy xuất có đủ thông tin trả lời, hay mọi ý AI viết đều đúng.

## 3. Chạy và xem top-k mà không cần API key

Mở PowerShell tại thư mục gốc dự án có `backend`, `frontend`, `data`:

```powershell
# Liệt kê course_id và số tài liệu đã nạp
.\.venv\Scripts\python.exe -m backend.rag_inspect

# Xem đúng các đoạn được bộ truy xuất chọn, không gọi AI
.\.venv\Scripts\python.exe -m backend.rag_inspect --course software_testing --question "Phân vùng tương đương là gì?" --top-k 3

# Chạy kiểm thử
.\.venv\Scripts\python.exe -m pytest backend/tests tests -q

# Chạy backend (mở /docs để thử API nếu chưa build frontend)
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
```

Kết quả lệnh inspect có `page`, `excerpt`, `score`, `passes_threshold`. Kết quả dưới ngưỡng vẫn được in để chẩn đoán nhưng không được đưa vào AI. API dùng top-k 3. Đây là tìm theo từ/ký tự với TF-IDF, chưa phải embedding ngữ nghĩa nên câu đồng nghĩa khác cách diễn đạt có thể tìm chưa tốt. Chưa cần vector database để chạy kho nhỏ này.

Để dùng phần giải thích AI, sao chép `.env.example` thành `.env`, rồi điền endpoint tương thích Chat Completions, model và khóa của nhà cung cấp bạn dùng. Không đưa khóa vào Git. Các đoạn vượt ngưỡng sẽ được gửi tới endpoint đã cấu hình. Chưa có cấu hình hợp lệ thì ứng dụng chỉ trích đoạn cục bộ. Hướng dẫn này không chọn hoặc thay endpoint của bạn.

Nếu `.venv` được chép từ máy khác không chạy được, tạo môi trường mới bằng Python 3.11+ và cài `requirements.txt`; môi trường ảo chứa đường dẫn phụ thuộc máy, không nên gửi chung với SRC.

## 4. Những thay đổi trong lần triển khai này

- Thêm chồng lấp 25 từ, giữ nguyên nguồn trang khi chia chunk.
- Với câu dạng “X là gì?”, tìm thêm cách diễn đạt “khái niệm X”, yêu cầu các từ của chủ đề xuất hiện trong đoạn; giảm điểm đoạn dưới 20 từ để hạn chế slide tiêu đề. Đây là heuristic ban đầu, có thể bỏ sót từ đồng nghĩa và cần đánh giá thêm.
- Dùng dịch vụ AI của backend thay cho dịch vụ của bản Streamlit.
- AI báo thiếu căn cứ → trả `insufficient_evidence`, không biến thành thành công.
- AI trả nguồn không hợp lệ hoặc lỗi dịch vụ → trả `ai_unavailable`, không âm thầm đổi sang đoạn tra cứu.
- Chỉ định dạng công thức cho câu trả lời AI; giữ nguyên trích đoạn khi tra cứu.
- Thêm `backend/tests/test_rag.py` và lệnh `backend.rag_inspect`.

## 5. Làm sao đánh giá có lấy đúng nguồn?

Tạo 20 câu phát triển do người đọc tài liệu xác nhận, gồm câu có đáp án và câu ngoài tài liệu. Mỗi câu ghi: `course_id`, câu hỏi, `document_id` đúng, trang PDF đúng, các ý cần có; với câu ngoài nguồn, để trống tài liệu/trang. Chạy inspect, lưu top-k và điểm rồi mở PDF đối chiếu. Đo Hit@3 = số câu có ít nhất một cặp (document_id, trang) đúng trong top 3 / tổng số câu có đáp án. Đánh giá riêng số câu ngoài tài liệu vẫn bị trả lời.

Ngưỡng 0.20 được giữ từ SRC, chưa được hiệu chỉnh bằng bộ câu hỏi học phần có nhãn. Điểm 0.8 không có nghĩa chắc chắn đúng 80%. Bộ kiểm thử tự động xác nhận cơ chế và các lỗi hồi quy; không thay thế đánh giá chất lượng trên tài liệu của nhóm. Giữ một bộ câu hỏi cuối riêng để kiểm tra sau khi chốt cấu hình.

Ca phát triển đã thử trên bộ PDF đi kèm: “Tập hợp là gì?” trong `toan_roi_rac`. Trước sửa, kết quả đầu là slide “Tổ hợp lặp”, trang PDF 36 của chương Tổ hợp. Sau sửa, kết quả đầu là trang PDF 2 của `Chuong 2 - Tap hop - 2020.pdf`, đoạn bắt đầu “Khái niệm cơ bản Tập hợp hình thành từ việc nhóm một số đối tượng…”. Ca này đã được dùng để cải thiện xếp hạng, không phải đánh giá độc lập.

Kiểm tra trong phiên triển khai: toàn bộ `backend/tests` và `tests` chạy qua (78 ca). Có một cảnh báo deprecation từ Starlette/TestClient về httpx. Phản hồi nhà cung cấp AI được giả lập tại biên HTTP để thử ID nguồn, từ chối và lỗi dịch vụ; chưa xác nhận chất lượng câu trả lời với một model/API thật.

Không có RAG nào bảo đảm AI đúng 100%. PDF scan cần OCR; bảng, công thức, nhiều cột hoặc font lỗi có thể trích xuất sai. Với thông tin quan trọng, mở trang gốc để đối chiếu.

## Tài liệu chính thức

- [PyMuPDF: trích xuất văn bản và thứ tự đọc](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
- [scikit-learn: TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [scikit-learn: cosine similarity](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html)
