# UniStudy AI (Phiên bản 2.0)

**Trợ lý học tập thông minh dành cho sinh viên đại học**  
Cuộc thi: *Xây dựng ứng dụng AI 2026* — Hướng C: Chatbot theo nhiệm vụ  
Nhóm: **K73E1 — Đội 1 (06 thành viên)**  
Kiến trúc: **React + TypeScript + Vite + Tailwind CSS + FastAPI (Python)**

---

## 1. Điểm nổi bật phiên bản 2.0

- **Frontend Hiện đại:** Chuyển đổi từ Streamlit sang **React + TypeScript + Tailwind CSS** với giao diện Modern Academic Workspace, tương thích desktop và mobile drawer.
- **Backend FastAPI Chuẩn REST:** Tách biệt rõ ràng tầng UI và tầng xử lý AI/PDF. Cung cấp API tài liệu trực tiếp tại `/docs`.
- **Tra cứu theo học phần:** Đặt câu hỏi để tìm đoạn trích, số trang và ảnh nguồn trong PDF của học phần đang chọn. Luồng tra cứu dùng TF-IDF, hỗ trợ câu hỏi tiếng Việt nhiều ý và có câu hỏi gợi ý cho các môn có sẵn.
- **Lịch sử theo học phần:** Mở lại hoặc đổi tên hội thoại đã lưu. Ứng dụng dùng ngữ cảnh trong cuộc trò chuyện để tra cứu câu hỏi nối tiếp.
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

Trên Windows, sau khi cài môi trường và build frontend, có thể chạy từ thư mục gốc bằng một trong các tệp sau.

- Bấm đúp `KHOI_DONG_CHATBOT.cmd` để khởi động UniStudy AI và mở trình duyệt. Nếu ứng dụng đang chạy, tệp mở phiên hiện tại.
- `CHAY_RAG.cmd` chạy ứng dụng với cấu hình AI hiện có.
- `CHAY_TRA_CUU.cmd` chạy tra cứu PDF cục bộ cho phiên đó.
- `CHAY_GEMINI.cmd` kiểm tra cấu hình trong `.env` rồi chạy ứng dụng. Đặt `UNISTUDY_AI_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` và điền `UNISTUDY_AI_MODEL` cùng `UNISTUDY_AI_API_KEY` theo `.env.example`. [Tài liệu Gemini](https://ai.google.dev/gemini-api/docs/openai)

Các lệnh cùng dùng cổng 8000. Để dừng phiên do tệp CMD khởi động, nhấn `Ctrl+C` trong cửa sổ CMD.

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
3. Nhập câu hỏi hoặc chọn câu gợi ý. Hệ thống tìm đoạn liên quan trong tài liệu của môn đang chọn và hiển thị trang nguồn để đối chiếu.
4. Bấm tên tài liệu hoặc trang nguồn để mở PDF trong ứng dụng. Dùng **Tìm trong PDF** để chuyển đến các trang chứa từ khóa.

Mỗi lượt nhận tối đa 5 PDF có văn bản, mỗi tệp tối đa 20 MB. PDF scan cần được nhận dạng chữ trước. Tệp tải lên được lưu trong `data/local_course_pdfs/`.

### Lịch sử hội thoại và câu hỏi nối tiếp

Chọn học phần rồi mở một cuộc trò chuyện trong **Lịch sử hội thoại** ở thanh bên. **Hội thoại mới** mở một cuộc trò chuyện trống và giữ các cuộc trước đó. Tên mặc định lấy từ câu hỏi đầu tiên. Bấm biểu tượng bút để đổi tên. Ứng dụng lưu lịch sử vào `data/conversations.json` trên máy chủ cục bộ và giữ một bản sao trong trình duyệt.

Ví dụ, sau khi hỏi “Phân vùng tương đương là gì?”, bạn có thể hỏi tiếp “Cho ví dụ?”. App dùng tối đa ba chủ đề gần nhất đã có nguồn trong cuộc trò chuyện đang mở để xác định chủ đề của câu hỏi nối tiếp. Kết quả tra cứu và ảnh trang vẫn lấy từ PDF của học phần đang chọn.

Xem cách kiểm tra các đoạn nguồn và chạy đánh giá tra cứu. [Hướng dẫn RAG](docs/RAG_GUIDE_VI.md)

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
| `PATCH` | `/api/conversations/{conversation_id}` | Đổi tên hội thoại bằng trường `title` |
| `GET` | `/api/documents/{document_id}/page/{page}` | Xem ảnh trích xuất của trang PDF tương ứng |
| `GET` | `/api/documents/{document_id}` | Tải tệp PDF tài liệu gốc |

---

## 6. Chạy kiểm thử tự động (Pytest)

```powershell
# Kiểm thử Backend API, RAG và Streamlit dự phòng
.\.venv\Scripts\python.exe -m pytest backend/tests tests -q
```
