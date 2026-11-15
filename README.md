# UniStudy AI (Phiên bản 2.0)

**Trợ lý học tập thông minh dành cho sinh viên đại học**  
Cuộc thi: *Xây dựng ứng dụng AI 2026* — Hướng C: Chatbot theo nhiệm vụ  
Nhóm: **K73E1 — Đội 1 (06 thành viên)**  
Kiến trúc: **React + TypeScript + Vite + Tailwind CSS + FastAPI (Python)**

Hướng dẫn đọc SRC, kiểm tra top-k và đối chiếu trang PDF: [RAG_GUIDE_VI.md](docs/RAG_GUIDE_VI.md).

---

## 1. Điểm nổi bật phiên bản 2.0

- **Frontend Hiện đại:** Chuyển đổi từ Streamlit sang **React + TypeScript + Tailwind CSS** với giao diện Modern Academic Workspace, tương thích desktop và mobile drawer.
- **Backend FastAPI Chuẩn REST:** Tách biệt rõ ràng tầng UI và tầng xử lý AI/PDF. Cung cấp API tài liệu trực tiếp tại `/docs`.
- **Tra cứu theo học phần:** Đặt câu hỏi để tìm đoạn trích, số trang và ảnh nguồn trong PDF của học phần đang chọn. Luồng tra cứu dùng TF-IDF và chạy cục bộ.
- **Giải thích bằng AI:** Dùng các đoạn PDF tìm được để giải thích chi tiết, so sánh, minh họa hoặc tạo câu hỏi ôn tập.
- **Lịch sử theo học phần:** Mở lại hội thoại đã lưu và dùng ngữ cảnh trong cuộc trò chuyện để tra cứu câu hỏi nối tiếp.
- **Tự quản lý học liệu:** Tạo học phần từ PDF hoặc bổ sung PDF vào môn đang chọn. Danh mục và tài liệu được lưu lại trên máy.
- **Học liệu có sẵn:** Tin học đại cương, Kiểm thử phần mềm, Phân tích thuật toán, Toán rời rạc và Thu thập & phân tích yêu cầu.
- **Phương án dự phòng:** Bản Streamlit cũ nằm trong `app.py`.

---

## 2. Hướng dẫn cài đặt và chạy ứng dụng

### Yêu cầu hệ thống
- **Python:** 3.11+
- **Node.js:** 20.19+ hoặc 22.12+ (hỗ trợ Vite)
- **Hệ điều hành:** Windows / Linux / macOS

---

### Cách 1: Chạy Fullstack (Khuyến nghị cho chấm sơ khảo & demo)

FastAPI phục vụ giao diện từ `frontend/dist`. Nếu vừa sửa mã giao diện, chạy `npm run build` trong thư mục `frontend` trước, rồi mở PowerShell tại thư mục gốc dự án.

```powershell
# Tại thư mục gốc D:\Chatbot UniStuAI
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
```

Mở trình duyệt tại: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**  
Tài liệu API Swagger: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

### Cách 2: Chạy chế độ Phát triển (Dev Mode: FastAPI + Vite HMR)

Mở **02 cửa sổ terminal**:

**Terminal 1 — Backend FastAPI:**
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend Vite:**
```powershell
cd frontend
npm run dev
```

Mở giao diện phát triển tại: **[http://localhost:5173](http://localhost:5173)** (Vite proxy tự động chuyển tiếp request `/api/*` về cổng 8000).

---

### Cách 3: Chạy ứng dụng Streamlit dự phòng

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
Mở tại: **[http://127.0.0.1:8501](http://127.0.0.1:8501)**

---

## 3. Cài đặt môi trường từ đầu (trên máy mới)

### 3.1. Cài đặt Python Backend
```powershell
# Tạo môi trường ảo
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện backend
pip install -r requirements.txt
```

Nếu dùng `uv`, chạy từng dòng trong PowerShell tại thư mục gốc.

```powershell
uv venv --python 3.11 .venv
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
```

### 3.2. Cài đặt Node.js Frontend
```powershell
cd frontend
npm install
npm run build
```

---

## 4. Thêm học phần và tra cứu

1. Mở **Thêm học phần** ở thanh bên, nhập tên, chọn PDF và bấm **Tạo học phần**. Ứng dụng sẽ mở môn vừa tạo.
2. Để bổ sung tài liệu, chọn môn cần cập nhật rồi mở **Thêm PDF vào học phần**. Chọn các PDF và bấm **Tải PDF lên**.
3. Nhập câu hỏi trong cuộc trò chuyện. Hệ thống tìm đoạn liên quan trong tài liệu của môn đang chọn và hiển thị trang nguồn để đối chiếu.
4. Để quản lý môn đang chọn, dùng **Đổi tên học phần** hoặc **Xóa học phần** ngay dưới **Thêm học phần**. Khi xác nhận xóa, môn được gỡ khỏi danh sách và tệp PDF vẫn được lưu trên máy.

Mỗi lượt nhận tối đa 5 PDF có văn bản, mỗi tệp tối đa 20 MB. PDF scan cần được nhận dạng chữ trước. Tệp tải lên được lưu trong `data/local_course_pdfs/`.

### Giải thích bài học bằng mô hình AI

1. Chọn học phần đã có PDF. Trong menu mô hình ở ô hỏi, chọn Gemini hoặc ChatGPT và nhập khóa của dịch vụ, hoặc chọn mô hình đã cài trong Ollama.
2. Chọn **Kiểu trả lời AI**. Dùng **Theo câu hỏi** để mô hình tự chọn cách trình bày, hoặc chọn **Giải thích chi tiết**, **So sánh**, **Ví dụ minh họa** hay **Câu hỏi ôn tập**.
3. Thử hỏi **Phân vùng tương đương là gì?** trong học phần **Kiểm thử phần mềm**. Mã như **[1]** cạnh nội dung tương ứng với nguồn được đánh số bên dưới. Mở trang PDF để đối chiếu quy tắc. Ví dụ và bài tập do mô hình soạn được ghi nhãn trong câu trả lời.

Chế độ **Tra cứu giáo trình (Offline)** hiển thị đoạn trích từ PDF trên máy. Khi mô hình gặp lỗi, bấm **Tra cứu giáo trình cho câu này** để xem đoạn trích. Chọn Ollama để xử lý học liệu trên máy, hoặc chỉ dùng Gemini và ChatGPT với học liệu được phép gửi đến dịch vụ đó.

### Học cùng AI

1. Mở **Học cùng AI** ở một trong hai học phần Chung kết. **Toán rời rạc** có bài **Phép hợp và phép giao**. **Thu thập và phân tích yêu cầu** có bài **Yêu cầu chức năng và phi chức năng**.
2. Trả lời câu kiểm tra ban đầu hoặc bấm **Xem giải thích trước**. Mỗi bài có phản hồi theo lỗi, ví dụ minh họa và nút mở đúng trang giáo trình.
3. Bấm **Tự làm bài mới**. Bạn có thể mở hai gợi ý theo thứ tự, hoặc xem lời giải sau khi thử. Bài làm đúng ở lần đầu và chưa mở gợi ý được ghi là **Đã tự làm đúng**. Bấm **Ôn với dữ kiện khác** để tiếp tục.

Luồng bài học cơ bản dùng phần giải thích soạn sẵn và chấm theo quy tắc của bài tập. Nút **Giải thích thêm với AI** dùng cấu hình máy chủ trong tệp `.env` theo mẫu `.env.example`. Đặt `UNISTUDY_AI_ENDPOINT`, `UNISTUDY_AI_MODEL` và `UNISTUDY_AI_API_KEY` của dịch vụ tương thích Chat Completions, sau đó khởi động lại backend. Tính năng này gửi trang học liệu minh họa được cấp phép và phản hồi chẩn đoán đã chuẩn hóa. Khi dịch vụ AI lỗi, sinh viên vẫn có thể tiếp tục làm bài.

Tiến độ được lưu ở `data/study_progress.sqlite3`. Trình duyệt giữ mã phiên theo học phần và chủ đề để lần sau mở lại đúng bước.

Cấu hình Gemini đã thử cho cả hai bài dùng `UNISTUDY_AI_MODEL=gemini-3.1-flash-lite` và `UNISTUDY_AI_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`. Điền khóa của bạn vào `UNISTUDY_AI_API_KEY` trong tệp `.env` cục bộ.

### Lịch sử hội thoại và câu hỏi nối tiếp

Chọn học phần rồi mở một cuộc trò chuyện trong **Lịch sử hội thoại** ở thanh bên. **Hội thoại mới** mở một cuộc trò chuyện trống và giữ các cuộc trước đó. Tên hội thoại lấy từ câu hỏi đầu tiên. Ứng dụng lưu lịch sử vào `data/conversations.json` trên máy chủ cục bộ và giữ một bản sao trong trình duyệt.

Ví dụ, sau khi hỏi “Phân vùng tương đương là gì?”, bạn có thể hỏi tiếp “Cho ví dụ?”. App dùng tối đa ba chủ đề gần nhất đã có nguồn trong cuộc trò chuyện đang mở để xác định chủ đề của câu hỏi nối tiếp. Kết quả tra cứu và ảnh trang vẫn lấy từ PDF của học phần đang chọn.

---

## 5. Hợp đồng API (REST API)

| Phương thức | Endpoint | Chức năng |
|---|---|---|
| `GET` | `/api/health` | Kiểm tra trạng thái máy chủ (`{"status": "ok"}`) |
| `GET` | `/api/courses` | Danh sách các học phần khả dụng |
| `POST` | `/api/courses` | Tạo học phần từ `course_name` và các tệp `files` dạng multipart |
| `GET` | `/api/courses/{course_id}/documents` | Danh sách tài liệu và số trang của học phần |
| `POST` | `/api/courses/{course_id}/documents` | Bổ sung các tệp `files` dạng multipart cho học phần |
| `POST` | `/api/chat` | Tra cứu `question` trong học phần `course_id`, với `previous_questions` tùy chọn gồm tối đa ba câu trước theo thứ tự thời gian |
| `GET` | `/api/study/{course_id}` | Liệt kê bài học có học liệu minh họa |
| `POST` | `/api/study/{course_id}/{topic_id}` | Mở hoặc tiếp tục phiên học bằng thao tác, mã phiên và phiên bản tiến độ |
| `GET` | `/api/documents/{document_id}/page/{page}` | Xem ảnh trích xuất của trang PDF tương ứng |
| `GET` | `/api/documents/{document_id}` | Tải tệp PDF tài liệu gốc |

---

## 6. Chạy kiểm thử tự động (Pytest)

```powershell
# Kiểm thử toàn bộ FastAPI, dịch vụ và Streamlit dự phòng
.\.venv\Scripts\python.exe -m pytest backend/tests tests -q

# Chạy riêng các tình huống Học cùng AI
.\.venv\Scripts\python.exe -m pytest backend/tests/test_study.py -v
```

Để chạy lại bài thử giao diện, build frontend rồi dùng máy chủ kiểm thử dưới đây. Nó phục vụ app với học liệu minh họa, tiến độ tạm và API mô phỏng có trích dẫn.

```powershell
# Cửa sổ thứ nhất
.\.venv\Scripts\python.exe -m tests.browser.study_server

# Cửa sổ thứ hai, dùng một phiên trình duyệt thử nghiệm mới
playwright-cli -s=unistudy-test open http://127.0.0.1:18173 --browser=msedge
playwright-cli -s=unistudy-test run-code --filename=tests/browser/study.js
# Chạy sau study.js vì bài thử này xóa một học phần trong dữ liệu tạm
playwright-cli -s=unistudy-test run-code --filename=tests/browser/course_management.js
playwright-cli -s=unistudy-test close
```
