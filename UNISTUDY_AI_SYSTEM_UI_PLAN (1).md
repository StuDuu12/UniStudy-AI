# UNISTUDY AI

## KẾ HOẠCH TRIỂN KHAI HỆ THỐNG & THIẾT KẾ UI/UX

**Kiến trúc:** React + TypeScript + Vite + Tailwind CSS + FastAPI (Python)  
**Phiên bản kế hoạch:** 2.0 — chuyển frontend từ Streamlit sang React  
**Ngày cập nhật:** 09/11/2026  
**Nhóm:** K73E1 — Đội 1 (06 thành viên)  
**Cuộc thi:** “Xây dựng ứng dụng AI” 2026 — dự kiến **Hướng C: Chatbot theo nhiệm vụ**  
**Hạn sơ khảo:** trước **23:50 ngày 12/11/2026**; mục tiêu nội bộ nộp **trước 20:00**.  
**Trạng thái đăng ký:** **CẦN XÁC NHẬN** quyền chuyển từ AI Review Analyzer (Hướng A) sang UniStudy AI (Hướng C). Cập nhật trên bảng đăng ký không tự động đồng nghĩa được chấp thuận.

> **Mục đích tài liệu:** Một nguồn thống nhất để 06 thành viên xây dựng, tích hợp, kiểm thử và bàn giao sản phẩm. Đây là **kế hoạch triển khai**, không phải khẳng định các chức năng đã hoàn thành hoặc các chỉ số đã được đo.

---

## 0. QUYẾT ĐỊNH THIẾT KẾ VÀ TÓM TẮT

**UniStudy AI** là trợ lý học tập dành cho sinh viên đại học. Sinh viên chọn học phần, đặt câu hỏi bằng tiếng Việt, hệ thống tìm kiếm trong học liệu PDF đã nạp và trả về **đoạn trích có nguồn** (chế độ tra cứu) hoặc **giải thích bằng mô hình ngôn ngữ dựa trên nguồn** (chế độ AI).

### 0.1. Điều thay đổi so với bản 1.0

| Hạng mục | Bản cũ | Bản 2.0 — chốt |
|---|---|---|
| Frontend | Streamlit | **React  + TypeScript + Tailwind CSS** |
| API ứng dụng | Gọi hàm Python nội bộ | **FastAPI / REST JSON** |
| UI | Widget Streamlit + CSS | **Component React, responsive, design tokens** |
| PDF, Retrieval, LLM | Python | **Giữ Python**, tận dụng các module đang phát triển |
| Chạy không khóa API | Chế độ tra cứu PDF | **Giữ bắt buộc**, là đường chạy tái lập cho người chấm |
| Streamlit hiện có | Ứng dụng chính | **Bảo lưu như bản dự phòng**, không phát triển tính năng song song |
| Triển khai | Chạy cục bộ | **Vite frontend + Uvicorn backend**, không bắt buộc hosting |

### 0.2. Định nghĩa hoàn thành (MVP)

1. Frontend React mở được, đẹp và dễ dùng trên desktop, có bố cục phù hợp mobile.
2. Chọn học phần từ **API thực**, không hardcode danh sách trong bản nghiệm thu.
3. `lookup` chạy **không cần API key**: hỏi → truy xuất học liệu thật → hiển thị đúng tài liệu, trang, đoạn trích.
4. `ai` chạy được **khi có cấu hình API hợp lệ**: hỏi → retrieval → kiểm tra căn cứ → LLM giải thích → hiển thị nguồn; nếu chưa cấu hình phải báo rõ.
5. Có thông báo phù hợp khi câu hỏi mơ hồ, không đủ căn cứ, không có tài liệu, backend lỗi, API AI lỗi.
6. Chọn học phần mới không trộn nguồn hoặc ngữ cảnh; mỗi câu hỏi xử lý độc lập trong MVP.
7. Có bộ học liệu **được phép chia sẻ** để ban giám khảo chạy lại và README chỉ rõ cách cài đặt.
8. Đủ báo cáo 03–05 trang, source, hướng dẫn chạy, video 02–03 phút và ít nhất 05 tình huống thử nghiệm thực tế.

### 0.3. Phạm vi thực hiện

| Mức | Chức năng | Quyết định |
|---|---|---|
| **P0 — bắt buộc** | Layout React; chọn học phần; chat; 02 chế độ; API; PDF thật; nguồn; trạng thái lỗi; kiểm thử; README | Triển khai trước |
| **P1 — nếu P0 ổn định** | Panel xem nguồn; mở PDF đúng trang; câu hỏi gợi ý từ học liệu; sao chép câu trả lời; thử nghiệm có/không RAG | Chỉ làm sau nghiệm thu P0 |
| **P2 — sau cuộc thi** | Đăng nhập, phân quyền, dashboard điểm, upload PDF tùy ý, tìm kiếm đa phương thức, học tập cá nhân hóa | **Không làm** trong sơ khảo |

**Cổng quan trọng:** Trước khi kết thúc **10/11**, React phải gọi FastAPI và nhận kết quả tra cứu từ PDF thật. Nếu không đạt, dừng trang trí UI và tập trung sửa tích hợp.

---

## 1. BÀI TOÁN, NGƯỜI DÙNG VÀ GIỚI HẠN

### 1.1. Vấn đề thực tế

Sinh viên sử dụng nhiều bài giảng, giáo trình, tài liệu PDF cho từng học phần. Tìm đúng trang để hiểu lại một khái niệm mất thời gian; chatbot phổ thông có thể trả lời khác với nguồn học liệu đang học. UniStudy AI tập trung vào việc **tra cứu đúng học phần và kiểm chứng được căn cứ**.

### 1.2. Đối tượng sử dụng

- **Sinh viên:** chọn môn, hỏi kiến thức, xem kết quả và mở nguồn tham khảo.
- **Nhóm phát triển/giám khảo:** chạy thử hệ thống với bộ học liệu demo được phép phân phối.
- **Ngoài phạm vi MVP:** tài khoản cá nhân, dữ liệu điểm số thật, hồ sơ sinh viên, công cụ quản trị giảng viên.

### 1.3. Học phần minh họa

- **Ưu tiên tích hợp trước:** *Tin học đại cương* — hiện giao diện Streamlit của nhóm đã liệt kê 04 PDF; kiểm tra thực tế các tệp trong máy/repository trước khi dùng.
- **Học phần thứ hai:** *Kiểm thử phần mềm* hoặc *Phân tích thuật toán*, chọn theo tài liệu có thể trích xuất và **được phép chia sẻ**.
- Nếu chưa có quyền phát hành các slide/giáo trình thực, tạo **bộ học liệu demo do nhóm tự biên soạn** dựa trên kiến thức cơ bản, có giấy phép/ghi nguồn phù hợp; vẫn có thể dùng PDF nội bộ để thử trên máy cá nhân.

### 1.4. Vai trò của AI và các giới hạn phải công bố

- Retrieval dùng TF-IDF/BM25 giúp **xếp hạng đoạn tài liệu**; bản thân nó không tạo lời giải thích.
- RAG kết hợp đoạn tài liệu và mô hình ngôn ngữ để **sinh câu giải thích có căn cứ**; vẫn có thể diễn giải sai và cần kiểm thử.
- Không khẳng định chatbot biết mọi kiến thức, đọc được mọi công thức/hình, chấm năng lực sinh viên hay hỗ trợ các câu hỏi ngoài kho dữ liệu.
- Kết quả chứa nguồn không tự động đồng nghĩa nội dung chính xác. Phải đối chiếu nguồn thủ công trong kiểm thử.

### 1.5. Tình huống người dùng mẫu

1. Chọn *Tin học đại cương*, hỏi “Hệ điều hành có chức năng gì?” → tra cứu trong tài liệu đúng môn.
2. Chọn *Kiểm thử phần mềm*, hỏi “Phân vùng tương đương khác giá trị biên ở đâu?” → nhận giải thích theo nguồn được cung cấp.
3. Hỏi nội dung không có trong tài liệu → trả `insufficient_evidence`.
4. Hỏi “Giải thích cái này” không có đối tượng → trả `needs_clarification`.
5. Không cấu hình API key → `lookup` vẫn hoạt động, `ai` báo chưa khả dụng.

---

## 2. KIẾN TRÚC HỆ THỐNG

```text
                   TRÌNH DUYỆT SINH VIÊN
    ┌───────────────────────────────────────────────┐
    │ FRONTEND: React + TypeScript + Tailwind       │
    │ Sidebar / Course / Chat / Source / Status     │
    │ API client, UI state, local session history   │
    └────────────────────┬──────────────────────────┘
                         │ REST JSON /api/*
                         ▼
    ┌───────────────────────────────────────────────┐
    │ BACKEND: FastAPI + Pydantic                   │
    │ validate → course → retrieval → evidence      │
    │            ↙                          ↘       │
    │      lookup mode                   ai mode    │
    │      snippets                  LLM with cites │
    └────────┬────────────────────────────┬─────────┘
             │                            │
             ▼                            ▼
    PDF pages → chunk metadata      API LLM (optional)
         ↓
    TF-IDF / BM25 index
         ↓
    evidence threshold + sources
```

### 2.1. Công nghệ chốt

| Tầng | Công nghệ | Lý do |
|---|---|---|
| UI | React + TypeScript | Tách component, giao diện linh hoạt, kiểm tra kiểu dữ liệu |
| Build | Vite (`react-ts`) | Khởi tạo nhanh, chạy dev riêng |
| Style | Tailwind CSS (Vite plugin), CSS variables | Thiết kế đồng nhất, responsive |
| Icon | `lucide-react` | Đồng nhất; không phụ thuộc emoji |
| HTTP | `fetch` + typed API wrapper | Không cần Axios ở MVP |
| State | React `useState`, `useEffect`, `useRef` | Chưa cần Redux/Zustand |
| Backend | FastAPI + Pydantic | API nhanh, schema và trang `/docs` hỗ trợ tích hợp |
| PDF | PyMuPDF | Trích xuất văn bản theo trang |
| Retrieval | scikit-learn TF-IDF ký tự/từ + cosine | Phù hợp kho nhỏ, chạy không cần API key |
| LLM | 01 nhà cung cấp đã được nhóm thử với khóa/hạn mức thật | Không ghi cứng nhà cung cấp chưa xác minh |
| Kiểm thử | `pytest` + CSV/JSON test cases; kiểm thử UI thủ công | Đủ minh chứng, hạn chế công cụ |
| Lưu trữ | JSON/CSV cục bộ, index có thể rebuild | Không cần MySQL, Redis, vector DB |

### 2.2. Hai chế độ vận hành

**`lookup` — Tra cứu tài liệu (mặc định)**

1. Nhận `course_id`, `question`.
2. Kiểm tra học phần, độ dài câu hỏi và trạng thái dữ liệu.
3. Truy xuất 1–3 đoạn liên quan theo môn.
4. Chỉ trả kết quả khi đạt chính sách đủ căn cứ.
5. Hiển thị **đoạn trích nguyên văn cùng tên tệp, trang**. Không gọi đây là “AI diễn giải”.
6. Không yêu cầu khóa hay kết nối API LLM.

**`ai` — Giải thích bằng AI (tùy chọn)**

1. Chạy các bước kiểm tra và truy xuất như `lookup`.
2. Nếu thiếu bằng chứng, dừng và trả trạng thái `insufficient_evidence` (không gọi LLM).
3. Gửi câu hỏi + đoạn liên quan cho mô hình đã được cấu hình.
4. Mô hình giải thích trong phạm vi tài liệu; backend gắn trích dẫn từ metadata thật.
5. Khi thiếu API key, trả `ai_unavailable` hoặc cho phép người dùng chuyển về `lookup`; không im lặng làm giả kết quả.

### 2.3. Ranh giới trách nhiệm

- **React:** hiển thị, điều hướng, trạng thái giao diện, gọi API, định dạng nội dung đã được backend trả về.
- **FastAPI:** kiểm tra đầu vào, xử lý chính sách truy xuất/căn cứ, nguồn, lỗi dịch vụ và LLM.
- **Không đặt API key LLM trong React**, `VITE_*` hoặc bundle trình duyệt.
- **Không để LLM tự đặt tên PDF/số trang**; nguồn được dựng từ kết quả retrieval.
- **Không đưa file PDF qua endpoint tùy ý** trong MVP; dùng danh mục tệp được quản lý trước.

---

## 3. QUẢN LÝ HỌC LIỆU THẬT VÀ TRUY XUẤT

### 3.1. Bộ dữ liệu chạy được cho giám khảo

Cần **hai nhóm học liệu tách biệt**:

| Bộ | Nguồn | Có nộp cùng source? |
|---|---|---|
| Tài liệu cá nhân/giảng viên đang sử dụng | PDF học phần thật đã có trên máy | **Chỉ khi có quyền phân phối** |
| Bộ demo hợp lệ | PDF nhóm tự biên soạn hoặc tài liệu có giấy phép cho phép chia sẻ | **Có**, ưu tiên làm đường chạy mặc định |

> **Bắt buộc:** Video và README phải dùng cùng một bộ demo đủ quyền chia sẻ. Tránh trường hợp video chạy được với tài liệu riêng nhưng giám khảo tải source lại không có dữ liệu.

### 3.2. Manifest và metadata

Mỗi tài liệu trong `data/manifest.json` nên có:

```json
{
  "course_id": "tin_hoc_dai_cuong",
  "document_id": "thdc_chuong_01",
  "filename": "Chuong_01_Gioi_thieu.pdf",
  "title": "Giới thiệu tin học đại cương",
  "page_count": 14,
  "permission": "team_authored_demo",
  "is_shareable": true
}
```

Mỗi đoạn tài liệu:

```json
{
  "chunk_id": "thdc_chuong_01_p03_c02",
  "course_id": "tin_hoc_dai_cuong",
  "document_id": "thdc_chuong_01",
  "page": 3,
  "text": "Nội dung trích xuất thật ở trang 3..."
}
```

Số trang quy định là **trang PDF theo thứ tự 1-based** (`page_index + 1`). Nếu tài liệu có số trang in trong nội dung khác số trang PDF, cần chú thích rõ. `document_id` là khóa an toàn để mở nguồn, không để frontend tự dựng đường dẫn file trên hệ điều hành.

### 3.3. Quy trình ingest PDF

1. Quét file trong danh mục cho phép; bỏ tệp hỏng và ghi log.
2. Trích xuất văn bản **từng trang** bằng PyMuPDF, kiểm tra lỗi mã hóa.
3. Tách theo mục/đoạn khi có thể; mục tiêu ban đầu **120–250 từ mỗi chunk**; không nối xuyên trang nếu muốn dẫn nguồn một trang.
4. Giữ `course_id`, `document_id`, `page`, `chunk_id`, `text` cho từng đoạn.
5. Tạo chỉ mục tìm kiếm **riêng hoặc lọc theo học phần**; chỉ tạo lại khi tài liệu thay đổi.
6. Kiểm tra 05 trang ngẫu nhiên mỗi môn với PDF gốc, đặc biệt phần biểu thức, bảng và mã giả.

**Giới hạn:** PDF scan, hình ảnh, công thức và bảng phức tạp có thể bị trích xuất sai; chưa dùng OCR trong P0. Khi tài liệu không đọc được, ghi rõ và loại khỏi phạm vi demo.

### 3.4. Retrieval và đủ căn cứ

- Baseline đề xuất: TF-IDF ký tự `char_wb` 3–5 gram + cosine; có thể bổ sung từ/ngữ nếu kịp.
- Trả **top-k**, ban đầu thử k = 3; các đoạn phải cùng `course_id`.
- Chọn ngưỡng `min_score` **trên bộ 20 câu phát triển**, trong đó có câu ngoài tài liệu. Không tự khẳng định một ngưỡng là đúng cho mọi học phần.
- `needs_clarification`: khi truy vấn không đủ chủ đề (vd. “giải thích cái đó”) → hỏi lại, tách biệt với `insufficient_evidence`.
- `insufficient_evidence`: câu hỏi rõ nhưng không tìm được đoạn đủ liên quan hoặc không có văn bản khả dụng.
- Lưu `top_score`, `threshold`, các đoạn được chọn vào log kiểm thử (không phải dữ liệu cá nhân).
- Chỉ số đánh giá: **Hit@k trúng trang**, tỷ lệ xử lý đúng câu ngoài phạm vi và đối chiếu trả lời với nguồn.

**Lưu ý:** Điểm cosine không phải “xác suất câu trả lời đúng”; UI không hiển thị phần trăm độ tin cậy giả tạo.

### 3.5. Chính sách hội thoại

- Mỗi câu hỏi trong MVP là một truy vấn **độc lập**. Lịch sử chỉ để hiển thị, không tự suy luận “nó/cái này” từ lượt trước.
- Khi đổi học phần, reset hội thoại hiển thị hoặc lưu riêng theo `course_id` ở client; không gửi lịch sử môn A sang môn B.
- Có thể làm follow-up theo ngữ cảnh ở P2 nhưng phải bổ sung kiểm thử riêng.

---

## 4. THIẾT KẾ UI/UX REACT — MODERN ACADEMIC WORKSPACE

### 4.1. Mục tiêu trực quan

Thiết kế như một **sản phẩm học tập thật**, không phải biểu mẫu kỹ thuật. Giao diện ưu tiên **khả năng đọc và kiểm chứng nguồn**; màu sắc tạo thương hiệu nhưng không áp đảo nội dung.

- Phong cách: Academic SaaS + AI Workspace.
- Giao diện sáng mặc định; sidebar nhận diện riêng; nền nội dung nhẹ, thẻ trắng.
- Tiếng Việt thống nhất, câu chữ rõ ràng; không tự đổi sang tiếng Anh trong thông báo.
- Responsive theo nguyên tắc mobile-first; không cuộn ngang.
- Hỗ trợ bàn phím, `focus-visible`, độ tương phản và trạng thái nút disabled.

### 4.2. Design system

| Token | Giá trị tham khảo | Dùng cho |
|---|---|---|
| `--primary` | `#4F46E5` | Nút chính, trạng thái chọn |
| `--primary-hover` | `#4338CA` | Hover |
| `--accent` | `#8B5CF6` | Điểm nhấn thứ cấp |
| `--cyan` | `#06B6D4` | Nhận diện nguồn/truy xuất |
| `--background` | `#F8FAFC` | Nền ứng dụng |
| `--surface` | `#FFFFFF` | Thẻ, chat, panel |
| `--text` | `#0F172A` | Tiêu đề và nội dung |
| `--muted` | `#64748B` | Chú thích |
| `--border` | `#E2E8F0` | Viền mảnh |
| `--success` | `#16A34A` | Tài liệu sẵn sàng |
| `--warning` | `#D97706` | Thiếu căn cứ |
| `--danger` | `#DC2626` | Lỗi |

- Font: Inter hoặc sans-serif hiển thị tiếng Việt tốt, dự phòng `system-ui`.
- Spacing: 4 / 8 / 12 / 16 / 24 / 32px.
- Radius: 10–14px (input/cards), 18–24px (khung nổi/hero).
- Shadow: nhẹ; không dùng glow rực rỡ quanh toàn bộ chat.
- Nút/điều khiển nên có vùng bấm ~40–44px; focus rõ cho thao tác bàn phím.
- Gradient Indigo → Violet **chỉ dùng một khu vực nổi bật** khi chưa có chat; không phủ các đoạn kiến thức dài.

### 4.3. Bố cục màn hình desktop

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│ UniStudy AI                                                Trợ lý học tập     │
├───────────────────────┬────────────────────────────────────────────────────────┤
│ SIDEBAR (260 px)      │ MAIN CONTENT (tối đa ~920 px)                          │
│                       │                                                        │
│ Thư viện học phần     │ [Tên học phần]    [Trạng thái học liệu]               │
│ [Chọn học phần ▾]     │                                                        │
│                       │ [Welcome hero / câu hỏi gợi ý]  (chỉ ở empty state)    │
│ Học liệu đã nạp       │                                                        │
│ • Chương 1.pdf        │ ┌────────────────────────────────────────────────────┐ │
│ • Chương 2.pdf        │ │ Người dùng hỏi                                     │ │
│                       │ └────────────────────────────────────────────────────┘ │
│ Chế độ trả lời        │ ┌────────────────────────────────────────────────────┐ │
│ ◉ Tra cứu tài liệu   │ │ Trả lời / đoạn trích                               │ │
│ ○ Giải thích AI      │ │ [Nguồn 1, trang X] [Nguồn 2, trang Y]             │ │
│                       │ └────────────────────────────────────────────────────┘ │
│ [+ Hội thoại mới]     │                                                        │
│                       │ [Hỏi về học phần...                         GỬI]     │
└───────────────────────┴────────────────────────────────────────────────────────┘
```

**Quy tắc:** Sau câu hỏi đầu tiên, banner chào và câu hỏi gợi ý thu gọn, tập trung không gian cho câu trả lời. Vùng nội dung không bị khóa ở giữa màn hình quá hẹp như bản Streamlit cũ.

### 4.4. Bố cục tablet/mobile

- Sidebar trở thành drawer mở bằng nút menu, có `aria-label` và đóng bằng Escape.
- Chat là một cột, căn vừa màn hình; source card đặt **ngay dưới câu trả lời** theo dạng accordion.
- Thanh nhập nằm cuối khung nội dung, không che câu trả lời và không bị bàn phím di động chặn hoàn toàn.
- Độ rộng mục tiêu: mobile 320–767px; tablet 768–1023px; desktop ≥1024px. Các mốc chỉ là hướng dẫn, cần kiểm tra bằng trình duyệt.
- Tên tài liệu dài tự xuống dòng/ellipsis có tooltip hoặc chế độ mở toàn bộ.

### 4.5. Danh sách thành phần React (P0)

| Component | Chức năng | Input/Props chính |
|---|---|---|
| `AppShell` | Tạo bố cục app, responsive | `children` |
| `AppSidebar` | Logo, danh mục học phần, mode, tài liệu | `courses`, `documents`, `mode` |
| `CourseSelector` | Chọn môn từ API | `courses`, `selected`, `onChange` |
| `DocumentList` | Liệt kê tài liệu có thật | `documents`, `loading` |
| `ChatPage` | Điều phối màn hình hội thoại | `courseId` |
| `WelcomePanel` | Lời chào + gợi ý khi chưa chat | `courseName`, `suggestions` |
| `MessageList` | Render danh sách câu hỏi/trả lời | `messages` |
| `ChatMessage` | Bubble user/assistant | `message`, `status` |
| `ChatComposer` | Nhập câu hỏi, Enter gửi, Shift+Enter xuống dòng | `onSend`, `disabled` |
| `SourceCard` | Tên file, trang, đoạn trích, nút mở | `source` |
| `ModeSwitch` | `lookup` / `ai` | `mode`, `aiAvailable` |
| `StatusNotice` | Loading/no evidence/error | `status`, `message` |
| `LoadingSkeleton` | Placeholder khi chờ | `variant` |

**P1:** `PdfPreviewDrawer`, `CopyAnswerButton`, `CourseSuggestionCards`, streaming messages. Chưa dùng router đa trang, state library lớn hoặc component library nặng nếu không cần.

### 4.6. Trạng thái UI và microcopy

| Trạng thái | UI | Câu chữ gợi ý |
|---|---|---|
| `empty` | Hero vừa phải + câu hỏi gợi ý | “Bạn muốn tìm hiểu kiến thức nào trong học phần này?” |
| `loading` | Spinner/skeleton, khóa nút gửi tạm thời | “Đang tìm nội dung liên quan trong học liệu...” |
| `success_lookup` | Đoạn trích + source cards | “Đã tìm thấy các đoạn học liệu liên quan.” |
| `success_ai` | Giải thích + source cards | “Câu trả lời được tạo từ học liệu đã truy xuất. Hãy đối chiếu nguồn.” |
| `insufficient_evidence` | Banner vàng, không có câu khẳng định suy đoán | “Chưa tìm thấy căn cứ đủ phù hợp trong tài liệu đã nạp.” |
| `needs_clarification` | Câu hỏi đề nghị làm rõ | “Bạn có thể nêu rõ khái niệm hoặc bài đang muốn hỏi không?” |
| `no_documents` | Empty state riêng | “Học phần này chưa có tài liệu khả dụng.” |
| `ai_unavailable` | Banner trung tính + gợi ý đổi mode | “Chế độ AI chưa được cấu hình. Bạn vẫn có thể tra cứu tài liệu.” |
| `error` | Thông báo thân thiện, nút thử lại | “Không thể kết nối hệ thống. Vui lòng thử lại.” |
| `invalid_input` | Inline validation | “Vui lòng nhập câu hỏi.” |

### 4.7. Quy tắc tương tác

1. Nút gửi disabled khi câu hỏi chỉ gồm khoảng trắng; chặn gửi liên tục tạo nhiều request.
2. Enter gửi câu hỏi, Shift+Enter xuống dòng; xử lý IME gõ tiếng Việt không gửi giữa lúc đang ghép ký tự.
3. Dùng `AbortController` để hủy/loại bỏ kết quả request cũ khi đổi học phần hoặc hội thoại mới.
4. Mỗi message có ID và timestamp cục bộ; câu trả lời lưu cả `status` và danh sách `sources`.
5. Khi đổi học phần, hiển thị hội thoại của môn đó hoặc xóa luồng cũ theo chính sách đã chốt; không trộn.
6. Không có `source` thì không hiển thị card giả hoặc số trang giả.
7. Khi click nguồn, chỉ mở endpoint file hợp lệ (`document_id` được backend xác thực); nếu chưa hỗ trợ xem file, hiển thị excerpt trong accordion.
8. Không hiển thị `score` như phần trăm chắc chắn. Nếu cần, ghi điểm truy xuất trong phần debug chỉ dành nhóm dev.
9. Luồng `lookup` và `ai` có nhãn rõ ràng, tránh tạo ấn tượng đoạn trích là lời diễn giải AI.
10. Không dùng `dangerouslySetInnerHTML` với nội dung tài liệu/LLM trong P0. Render chuỗi an toàn; nếu dùng Markdown renderer về sau phải kiểm soát HTML/links.

### 4.8. Thẩm mỹ và accessibility

- Chỉ một màu chính (Indigo), một màu nhấn (Violet/Cyan); không thêm màu tràn lan.
- Tiêu đề chính 24–32px, chữ chat ~15–16px, chú thích ≥12px; line-height 1.5–1.7.
- Phản hồi trạng thái phải có **chữ** ngoài màu sắc; error/warning không chỉ thể hiện bằng đỏ/vàng.
- `aria-live="polite"` cho kết quả mới; label rõ cho nút icon; focus order hợp lý.
- Kiểm tra 3 kích thước: 375px, 768px, 1366px; không cắt chữ/nguồn.

---

## 5. HỢP ĐỒNG API GIỮA REACT VÀ FASTAPI

**Tiền tố:** `/api` — frontend dev dùng Vite proxy để tránh CORS; nếu chạy hai origin khác nhau mà không proxy thì backend chỉ cho phép các origin xác định.

### 5.1. Bảng endpoint P0

| Method | Endpoint | Mục đích | Yêu cầu |
|---|---|---|---|
| `GET` | `/api/health` | Kiểm tra backend | `{ "status": "ok" }` |
| `GET` | `/api/courses` | Danh sách môn có học liệu | ID ổn định, tên, số tài liệu |
| `GET` | `/api/courses/{course_id}/documents` | Danh sách tài liệu môn | Không trả đường dẫn file hệ thống |
| `POST` | `/api/chat` | Tra cứu/giải thích | JSON contract bên dưới |
| `GET` | `/api/documents/{document_id}` | Xem/tải tệp demo được phép chia sẻ | **P1**, cần kiểm tra quyền và danh mục hợp lệ |

### 5.2. `GET /api/courses`

```json
{
  "courses": [
    {
      "course_id": "tin_hoc_dai_cuong",
      "course_name": "Tin học đại cương",
      "document_count": 4,
      "status": "ready"
    }
  ]
}
```

`document_count: 4` chỉ là **ví dụ schema tương ứng với ảnh ứng dụng hiện tại**; API thật phải tính từ dữ liệu đã nạp. Không hardcode như số liệu kiểm thử.

### 5.3. `GET /api/courses/{course_id}/documents`

```json
{
  "documents": [
    {
      "document_id": "thdc_chuong_01",
      "document_name": "Chuong_01_Gioi_thieu.pdf",
      "page_count": 14
    }
  ]
}
```

### 5.4. `POST /api/chat` — request

```json
{
  "course_id": "tin_hoc_dai_cuong",
  "question": "Hệ điều hành có những chức năng gì?",
  "mode": "lookup"
}
```

- `mode` nhận **chính xác** `lookup` hoặc `ai`.
- Trim khoảng trắng; từ chối chuỗi rỗng.
- Giới hạn số ký tự ở backend (đề xuất 2.000 ký tự trong MVP); frontend đồng bộ validation nhưng backend là nguồn kiểm soát cuối.

### 5.5. `POST /api/chat` — response chuẩn

```json
{
  "status": "success",
  "answer": "Đã tìm thấy các đoạn học liệu liên quan.",
  "mode": "lookup",
  "sources": [
    {
      "chunk_id": "thdc_chuong_01_p03_c02",
      "document_id": "thdc_chuong_01",
      "document_name": "Chuong_01_Gioi_thieu.pdf",
      "page": 3,
      "excerpt": "Đoạn trích thực từ tài liệu...",
      "score": 0.48
    }
  ],
  "message": null
}
```

**Lưu ý:** Toàn bộ nội dung `answer`, `excerpt`, `score` và `page` bên trên chỉ để giải thích định dạng JSON, không phải kết quả thực nghiệm đã có. Backend chỉ được trả nguồn thật được truy xuất.

### 5.6. Các status hợp lệ

```typescript
type ChatStatus =
  | 'success'
  | 'insufficient_evidence'
  | 'needs_clarification'
  | 'no_documents'
  | 'ai_unavailable'
  | 'error';

type ChatMode = 'lookup' | 'ai';

interface ChatRequest {
  course_id: string;
  question: string;
  mode: ChatMode;
}

interface Source {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page: number;
  excerpt: string;
  score: number | null;
}

interface ChatResponse {
  status: ChatStatus;
  answer: string;
  mode: ChatMode;
  sources: Source[];
  message: string | null;
}
```

**Quy ước HTTP:**

- `200` cho request hợp lệ, kể cả `insufficient_evidence` / `needs_clarification` (trạng thái nghiệp vụ bình thường).
- `422` khi payload không đúng schema; frontend hiển thị lỗi nhập liệu.
- `404` nếu `course_id` không tồn tại hoặc document được yêu cầu không hợp lệ.
- `503` khi dịch vụ cần thiết không hoạt động; trả thông báo an toàn, không lộ traceback.
- `ai_unavailable` có thể trả HTTP 200 ở mức nghiệp vụ khi mode AI chưa cấu hình; **thống nhất duy nhất một quy ước** ở frontend/backend trước khi code.

### 5.7. API client React — ví dụ tối thiểu

```ts
// frontend/src/services/api.ts
import type { ChatRequest, ChatResponse } from '../types/api';

const API_BASE = '/api';

export async function sendChat(
  payload: ChatRequest,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Yêu cầu thất bại (HTTP ${response.status})`);
  }
  return (await response.json()) as ChatResponse;
}
```

Không dùng `setTimeout` để giả lập câu trả lời trong bản nộp. Dữ liệu mock chỉ tồn tại trong giai đoạn thiết kế UI và được phân biệt với dữ liệu thật.

### 5.8. Vite proxy — cấu hình đề xuất

```ts
// frontend/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
```

Frontend gọi URL tương đối `/api/...`. Khi build production hoặc phục vụ tĩnh từ FastAPI, phải bảo đảm proxy/ngược tuyến tương ứng; **Vite proxy chỉ hoạt động khi chạy dev server**.

---

## 6. THIẾT KẾ FASTAPI VÀ CẤU TRÚC BACKEND

### 6.1. Luồng `POST /api/chat`

```text
request
  │
  ├─ kiểm tra course_id / question / mode
  ├─ kiểm tra học phần có dữ liệu
  ├─ kiểm tra câu hỏi mơ hồ
  ├─ retrieval lọc theo course_id
  ├─ chính sách đủ căn cứ
  │   ├─ không đạt → insufficient_evidence
  │   ├─ lookup → snippets + source metadata
  │   └─ ai → kiểm tra API key → gọi LLM → answer + sources
  └─ JSON response thống nhất
```

### 6.2. Skeleton FastAPI cho team backend (định nghĩa contract)

```python
# backend/main.py — skeleton minh họa, chưa phải RAG hoàn chỉnh
from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="UniStudy AI API")

class ChatRequest(BaseModel):
    course_id: str
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal["lookup", "ai"] = "lookup"

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Các endpoint courses/documents/chat do team backend triển khai
# theo schema mục 5. Không trả dữ liệu giả trong bản nghiệm thu.
```

API key dùng biến môi trường backend (`LLM_API_KEY` hoặc tên được thống nhất). Không commit `.env`, file index chứa tài liệu hạn chế hoặc đường dẫn nhạy cảm. Chỉ mở CORS cho origin đã xác định nếu không dùng proxy.

### 6.3. Kiểm soát lỗi và an toàn

- Đọc chỉ từ `document_id` trong manifest, không nhận đường dẫn PDF tự do từ user.
- Giới hạn độ dài câu hỏi và số đoạn đưa vào prompt, tránh gọi API vượt mức.
- Hạn chế logging nội dung chat; không đưa thông tin cá nhân vào bản demo.
- Nội dung PDF là **dữ liệu không đáng tin cậy**, không phải chỉ thị cho mô hình hoặc hệ thống.
- Lỗi API không được trả thông tin khóa, traceback hoặc biến môi trường vào JSON.
- Frontend chỉ render text an toàn, không thực thi HTML/JavaScript trong câu trả lời.

---

## 7. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
unistudy-ai/
├── frontend/                            # React + TS + Vite
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx
│   │   │   │   ├── AppSidebar.tsx
│   │   │   │   └── AppHeader.tsx
│   │   │   ├── courses/
│   │   │   │   ├── CourseSelector.tsx
│   │   │   │   └── DocumentList.tsx
│   │   │   ├── chat/
│   │   │   │   ├── ChatPage.tsx
│   │   │   │   ├── ChatComposer.tsx
│   │   │   │   ├── ChatMessage.tsx
│   │   │   │   └── MessageList.tsx
│   │   │   ├── sources/
│   │   │   │   └── SourceCard.tsx
│   │   │   └── shared/
│   │   │       ├── ModeSwitch.tsx
│   │   │       ├── StatusNotice.tsx
│   │   │       └── LoadingSkeleton.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts
│   │   ├── services/
│   │   │   ├── api.ts                    # HTTP client thật
│   │   │   └── mockApi.ts                # Chỉ cho DEV UI
│   │   ├── types/
│   │   │   └── api.ts                    # API contract
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                              # FastAPI + PDF + RAG
│   ├── main.py
│   ├── routers/
│   │   ├── courses.py
│   │   └── chat.py
│   ├── schemas/
│   │   └── chat.py
│   ├── services/
│   │   ├── ingest.py
│   │   ├── retrieval.py
│   │   ├── evidence.py
│   │   └── llm_service.py
│   ├── data/
│   │   ├── manifest.json
│   │   ├── demo_licensed/               # PDF được phép nộp
│   │   ├── private_local/               # .gitignore
│   │   └── index/                       # chỉ mục build lại được
│   ├── tests/
│   │   ├── dev_questions.csv
│   │   ├── final_questions.csv
│   │   └── test_api.py
│   ├── requirements.txt
│   └── .env.example
│
├── docs/
│   ├── report.pdf
│   ├── test_results.csv
│   ├── demo.mp4
│   └── data_manifest.md
├── README.md
├── .gitignore
└── UNISTUDY_AI_SYSTEM_UI_PLAN.md
```

**Git:** `main` luôn ở trạng thái chạy được; các thành viên làm trên nhánh `feature/ui`, `feature/data`, `feature/retrieval`, `feature/llm`, `feature/api`, `feature/tests`. Gộp branch qua kiểm tra chéo, không đẩy `.env` hay tài liệu không có quyền phân phối.

---

## 8. KHỞI TẠO VÀ CHẠY TRÊN WINDOWS

### 8.1. Điều kiện máy

- Node.js tương thích phiên bản Vite đang dùng (kiểm tra tài liệu Vite; yêu cầu hiện tại từ hướng dẫn chính thức: Node.js **20.19+ hoặc 22.12+**).
- Python 3.11 khuyến nghị cho backend.
- VS Code, Git, PowerShell.

### 8.2. Khởi tạo frontend

```powershell
mkdir unistudy-ai
cd unistudy-ai
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite lucide-react
```

Cấu hình `vite.config.ts` theo **Mục 5.8** và thêm dòng vào `src/index.css`:

```css
@import "tailwindcss";
```

Chạy UI:

```powershell
npm run dev
```

Địa chỉ mặc định thường là `http://localhost:5173` (dùng URL thực tế in ở terminal).

### 8.3. Khởi tạo backend

```powershell
# Mở terminal khác tại thư mục gốc unistudy-ai
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install fastapi "uvicorn[standard]" pymupdf scikit-learn python-dotenv pytest
python -m pip freeze > requirements.txt
uvicorn main:app --reload --port 8000
```

Nếu PowerShell chặn script, sử dụng `cmd.exe` và `.venv\Scripts\activate.bat` hoặc lệnh chạy Python trực tiếp trong `.venv\Scripts\python.exe` thay vì vô hiệu hóa chính sách bảo mật toàn hệ thống.

### 8.4. Chạy đồng thời

1. Terminal 1: `uvicorn main:app --reload --port 8000` trong `backend/`.
2. Terminal 2: `npm run dev` trong `frontend/`.
3. Kiểm tra `http://127.0.0.1:8000/api/health` và `http://localhost:5173`.
4. Test frontend gọi `/api/courses` và `/api/chat` qua Vite proxy.
5. Kiểm tra build frontend: `npm run build`.

**Khi nộp:** README phải ghi cả hai lệnh chạy; không chỉ ghi URL localhost hoặc đưa code mà không có dữ liệu mẫu.

### 8.5. Tích hợp phần Python đã viết cho Streamlit

- Giữ file xử lý PDF, retrieval, evidence và LLM dưới `backend/services/`.
- Loại bỏ `st.*` khỏi core logic; service Python không được phụ thuộc Streamlit.
- FastAPI gọi service và biến kết quả thành JSON theo schema Mục 5.
- Không yêu cầu tái huấn luyện, không chuyển code RAG sang TypeScript.
- Bảo lưu bản Streamlit hiện chạy trong nhánh/tag riêng để dự phòng.

---

## 9. PHÂN CÔNG 06 THÀNH VIÊN

| Thành viên | Vai trò chính | Đầu ra cần bàn giao |
|---|---|---|
| **Chu Quang Duy** | **React UI/UX**, chốt contract, điều phối tích hợp, xác nhận đăng ký | `frontend/` hoàn chỉnh, kiểm tra API thật, demo UI, phối hợp hồ sơ |
| **Nguyễn Tiến Đạt** | Học liệu, manifest, PDF ingest, bộ phát triển | PDF demo hợp lệ, `manifest.json`, `ingest.py`, 20 câu dev |
| **Nguyễn Thành Đạt** | Retrieval, chia đoạn, căn cứ và ngưỡng | `retrieval.py`, `evidence.py`, hit@k và log thử trên bộ dev |
| **Lê Văn Khoa** | LLM / prompt / xử lý API | `llm_service.py`, 01 lời gọi AI thật, lỗi thiếu khóa, trả lời có nguồn |
| **Nguyễn Ngọc Đức** | **FastAPI + tích hợp backend**, đóng gói | Router `/api/*`, Pydantic schema, CORS/proxy, README kỹ thuật |
| **Đinh Thái Bình** | Kiểm thử độc lập, minh chứng, video và hỗ trợ báo cáo | 12 câu final, bảng test thực tế, thử máy sạch, video 2–3 phút |

**Nguyên tắc phụ thuộc:**

- Duy và Đức chốt JSON schema, status và endpoint **trước** khi tiếp tục tách nhánh.
- Tiến Đạt bàn giao một PDF/index thật sớm cho Thành Đạt.
- Khoa thử API độc lập bằng dữ liệu nguồn mẫu; không chờ toàn bộ retrieval.
- Duy gọi mock API trong giai đoạn dựng UI; Đức thay bằng FastAPI **không cần Duy viết lại component**.
- Bình giữ 12 câu cuối độc lập, không để nhóm dùng chúng để chọn tham số.

---

## 10. TIẾN ĐỘ 09–12/11/2026

> **Lưu ý:** Mốc giờ dưới đây là thời điểm điều phối nội bộ được đề xuất trong chiều 09/11, không phải thời hạn chính thức của Ban tổ chức. Nếu một mốc đã qua, xử lý ngay và ghi nhận trạng thái thực tế, không điền lùi kết quả chưa có.

### 09/11 — Chốt khả năng đổi hướng + skeleton UI/API

- **Duy/trưởng nhóm:** liên hệ BTC ngay, xin xác nhận đổi sản phẩm và hướng dự thi; đặt mốc quyết định nội bộ **trong tối 09/11**, không tự coi im lặng là đồng ý.
- **Duy:** tạo Vite React TS, theme, Sidebar, CourseSelector, ChatComposer, ChatMessage, SourceCard. Render mock đúng schema.
- **Đức:** tạo FastAPI skeleton, `/api/health`, `/api/courses`, `/api/chat` với adapter để thay dữ liệu thật.
- **Tiến Đạt:** cung cấp manifest + ít nhất một PDF demo được phép chia sẻ; ingest theo trang.
- **Thành Đạt:** tìm kiếm top-3 đoạn từ tài liệu thật, có metadata và score.
- **Khoa:** thử 01 request AI với dịch vụ/khóa đã được nhóm cấu hình; lưu kết quả kiểm thử (không lưu khóa).
- **Bình:** chuẩn bị test schema và các câu hỏi có trang tham chiếu.

**Cổng cuối ngày:** `/api/health` hoạt động; React hiển thị giao diện; backend tìm được đoạn nguồn thật trên một học phần; xác nhận được tình trạng đăng ký.

### 10/11 — Ghép React + FastAPI và đóng băng tính năng

- React gọi **API thật** từ FastAPI cho ít nhất một môn, sau đó thêm môn thứ hai.
- Có chế độ `lookup` không khóa và chế độ `ai` theo cấu hình thực tế.
- Chốt chunk size/top-k/ngưỡng trên 20 câu dev; kiểm tra câu ngoài phạm vi và câu mơ hồ.
- Test chuyển môn, lỗi API, không có PDF, sai course_id, câu hỏi rỗng.
- **18:00:** đóng băng tính năng P0; từ đây chỉ ưu tiên lỗi nghiệm thu và UI cốt lõi.

**Cổng ngày 10/11:** chọn môn → gửi câu hỏi → nhận **nguồn PDF thật từ FastAPI trên UI React**; có thể chạy lại theo README.

### 11/11 — Kiểm thử, hồ sơ và video

- Bình chạy **12 ca final giữ riêng**, ghi đầu vào, mong đợi, thực tế, nhận xét.
- Nhóm đối chiếu nguồn/trang theo PDF demo, ghi số câu đúng và số lỗi, không phóng đại độ chính xác.
- Chạy `npm run build`, kiểm tra API, cài đặt trên máy khác từ README.
- Chuẩn bị báo cáo 03–05 trang, video 02–03 phút, screenshot, dữ liệu mẫu.
- Chỉ sửa lỗi nghiêm trọng sau khi mở bộ final; nếu đổi tham số, phải ghi rõ việc đánh giá không còn độc lập hoàn toàn.

### 12/11 — Chốt và nộp

- Trước 16:00: khóa bản source, rà soát `.gitignore`, secrets, manifest, giấy phép, README, video, test result.
- Mở liên kết bằng tài khoản ngoài nhóm để kiểm tra quyền truy cập.
- Mục tiêu gửi hồ sơ **trước 20:00**; hạn BTC là **trước 23:50 ngày 12/11/2026**.
- Địa chỉ và định dạng gửi tuân theo văn bản thể lệ đã cung cấp; trưởng nhóm kiểm tra một lần trước khi gửi.

### Nếu được vào chung kết

- Ngày 13/11: chấm sơ khảo; ngày 14/11: công bố nhóm vào vòng chung kết.
- Trước 20:00 ngày 15/11: nộp bản chỉnh sửa, slide và bảng tổng hợp góp ý, ≥10 ca thử gồm cả ca lỗi.
- Chiều 16/11: 05 phút giới thiệu, 07 phút demo, 08 phút phản biện.

---

## 11. KIỂM THỬ VÀ CHỈ SỐ ĐÁNH GIÁ

### 11.1. Tách dữ liệu phát triển và dữ liệu kiểm thử

| Bộ | Mục đích | Ai làm | Cách dùng |
|---|---|---|---|
| **20 câu dev** | Chọn chunk size, top-k, ngưỡng | Tiến Đạt + Thành Đạt | Có thể lặp nhiều lần |
| **12 câu final** | Đánh giá sau khi chốt tham số | Bình, kiểm tra chéo | Chỉ mở sau khi khóa cấu hình |

Các câu hỏi cần có `id`, `course_id`, `question`, `case_type`, `reference_document`, `reference_page(s)` khi tồn tại, `expected_status`, `actual_status`, `observed_sources`, `result`, `notes`. Câu ngoài phạm vi **không có trang đáp án**, phải chấm riêng.

### 11.2. Bộ tình huống tối thiểu

| ID | Tình huống | Kỳ vọng |
|---|---|---|
| T01 | Hỏi định nghĩa có trong học liệu | Đoạn nguồn đúng |
| T02 | So sánh hai khái niệm | Có nguồn liên quan |
| T03 | Câu hỏi diễn đạt lại | Truy xuất đúng dù khác từ |
| T04 | Hỏi môn thứ hai | Chỉ lấy nguồn môn thứ hai |
| T05 | Đổi môn rồi hỏi | Không trộn lịch sử/nguồn |
| T06 | Câu hỏi rõ nhưng ngoài tài liệu | `insufficient_evidence` |
| T07 | Câu hỏi “cái đó”/mơ hồ | `needs_clarification` |
| T08 | Câu hỏi rỗng | UI chặn hoặc backend `422` |
| T09 | Tài liệu là ảnh/công thức không trích xuất được | Cảnh báo giới hạn |
| T10 | Câu hỏi mang lệnh thao túng tài liệu | Không thực thi chỉ thị ngoài nhiệm vụ |
| T11 | Mất kết nối backend/API LLM lỗi | Error state, không lộ secrets |
| T12 | Kiểm tra từng source card | Trùng tệp/trang/đoạn PDF thật |

### 11.3. Chỉ số nên báo cáo

- **Hit@k theo trang** = số câu có ít nhất một trang tham chiếu đúng trong top-k / số câu có trang đáp án.
- **Tỷ lệ từ chối đúng** = số câu ngoài phạm vi được từ chối đúng / tổng câu ngoài phạm vi.
- **Tỷ lệ dẫn nguồn hợp lệ** = số nguồn hiển thị khớp tệp/trang/đoạn thật / tổng nguồn kiểm tra.
- **Chất lượng trả lời AI**: đánh giá thủ công 0–2 theo căn cứ, tính đầy đủ, đúng nội dung; không gọi đó là độ chính xác khoa học trên tập lớn.
- **Thời gian phản hồi**: có thể ghi nhận, nhưng không khẳng định KPI khi chưa đo.

Mọi tỷ lệ phải đi kèm **tử số/mẫu số** (ví dụ 7/9) vì bộ 12 câu nhỏ. Không dùng test final để điều chỉnh ngưỡng rồi tiếp tục gọi đó là đánh giá độc lập.

### 11.4. Kiểm thử UI/API

- React build thành công và không có lỗi runtime lớn trong console.
- Đổi môn hủy request cũ hoặc bỏ kết quả cũ; không lẫn nguồn.
- Không tạo tin nhắn trùng khi Enter liên tiếp.
- Không render HTML script trong câu trả lời API.
- Màn hình 375px/768px/1366px không cuộn ngang, nút gửi dễ thao tác.
- UI hiện đúng status kể cả khi server trả `422`, `404`, `503`.
- Chạy không có `.env` LLM: `lookup` vẫn hoạt động, `ai` báo rõ.

---

## 12. HỒ SƠ DỰ THI VÀ DEMO

### 12.1. Bộ hồ sơ sơ khảo bắt buộc

1. **Báo cáo 03–05 trang:** bài toán/người dùng, chức năng, dữ liệu và quyền dùng, giải pháp, vai trò AI, thử nghiệm thực tế, giới hạn, phân công.
2. **Source code:** `frontend/`, `backend/`, mã truy xuất, các tệp cấu hình có thể chạy lại.
3. **README + dữ liệu mẫu hợp lệ:** hướng dẫn cài Node/Python, chạy 2 server, cấu hình API, các lỗi thường gặp.
4. **Video 02–03 phút:** làm rõ câu hỏi, nguồn PDF, chế độ không khóa, chế độ AI (nếu đã chạy được).
5. **Bảng ít nhất 05 tình huống:** đầu vào, kết quả mong đợi, kết quả thực tế, nhận xét; mục tiêu nội bộ 12 ca final.

**Không được nộp:** API key, mật khẩu, dữ liệu cá nhân nhạy cảm, PDF không có quyền phát hành, số liệu test bịa hoặc screenshot demo dùng mock mà ghi là kết quả thật.

### 12.2. Kịch bản video 02–03 phút

| Thời lượng | Nội dung |
|---|---|
| 00:00–00:20 | Vấn đề sinh viên tìm kiến thức trong nhiều PDF |
| 00:20–00:40 | UI React UniStudy AI, chọn học phần |
| 00:40–01:15 | Tra cứu PDF thật không cần API key, hiện source card |
| 01:15–01:50 | Nếu có API: giải thích AI dựa trên đoạn nguồn |
| 01:50–02:15 | Hỏi ngoài tài liệu, hệ thống từ chối hợp lý |
| 02:15–02:40 | Minh chứng nhóm tự xây dựng, giới hạn, kết quả thử thực tế |

Giữ video dự phòng cho chung kết nhưng vẫn phải có ứng dụng chạy thực tế.

---

## 13. PHƯƠNG ÁN DỰ PHÒNG VÀ QUYẾT ĐỊNH ĐỔI HƯỚNG

1. Đã đăng ký ban đầu **AI Review Analyzer (Hướng A)**. Muốn đổi sang **UniStudy AI (Hướng C)** phải xác nhận từ Ban tổ chức.
2. Nếu **được chấp thuận**, chốt duy nhất UniStudy AI và hoàn thiện React + FastAPI.
3. Nếu **không được chấp thuận**, quay lại **đúng sản phẩm AI Review Analyzer đã đăng ký**, dùng kế hoạch/dữ liệu/model đã chuẩn bị. **Không** tự đổi sang AI Course Feedback Analyzer (sản phẩm thứ ba).
4. Khi đang chờ phản hồi, bảo lưu code Streamlit và source Hướng A, **không phân nhân lực chạy song song hai sản phẩm đầy đủ**.
5. Nếu không có phản hồi, đây là **trạng thái chưa xác nhận**, không phải đồng ý ngầm. Trưởng nhóm phải chốt quyết định hợp lệ và hồ sơ đăng ký với BTC trong tối 09/11; ghi lại kết quả.

> **Ràng buộc quan trọng:** Chuyển Streamlit → React là thay **công nghệ UI** trong UniStudy AI; đổi AI Review Analyzer → UniStudy AI là thay **sản phẩm/hướng đăng ký**. Hai quyết định khác nhau và phải quản lý tách biệt.

---

## 14. RỦI RO VÀ CÁCH GIẢM THIỂU

| Rủi ro | Ảnh hưởng | Cách xử lý |
|---|---|---|
| Đổi hướng chưa được phép | Hồ sơ có thể không hợp lệ | Xác nhận BTC, giữ Hướng A làm fallback |
| React và backend không khớp JSON | Không chạy được khi demo | Chốt schema/status trước, test API contract |
| Tốn thời gian trang trí UI | Trễ chức năng chính | P0 trước; cổng ngày 10/11, khóa tính năng |
| Không có API key khi chấm | Không chạy được AI mode | `lookup` độc lập, README rõ, AI mode chỉ bật khi cấu hình |
| PDF không được phép chia sẻ | Thiếu dữ liệu khi giám khảo cài | Bộ demo tự biên soạn/có quyền phân phối |
| PDF đọc sai công thức/hình | Nguồn/giải thích sai | Chọn văn bản rõ; giới hạn MVP |
| Retrieval nhầm môn/nguồn | Mất độ tin cậy | Lọc `course_id`, gắn nguồn từ metadata, kiểm thử T04/T05 |
| Hỏi ngoài phạm vi vẫn sinh đáp án | Sai yêu cầu cốt lõi | Ngưỡng trên dev set, không gọi LLM khi thiếu căn cứ |
| Mất mạng/API lỗi | Demo gián đoạn | Error state + chế độ không khóa + video dự phòng |
| Frontend lộ API key | Rủi ro bảo mật | Chỉ giữ khóa ở backend `.env`, không dùng `VITE_*` |

---

## 15. CHECKLIST NGHIỆM THU THEO NGƯỜI

### 15.1. Duy — React UI/UX

- [ ] Khởi tạo Vite React TS + Tailwind Vite plugin và chạy `npm run dev`.
- [ ] Dựng `AppShell`, Sidebar responsive, Header, CourseSelector.
- [ ] Dựng Chat Page, lịch sử, input, gửi Enter/Shift+Enter, trạng thái loading.
- [ ] Hiển thị câu trả lời phân biệt lookup và AI.
- [ ] Hiển thị SourceCard bằng metadata API thật, không hardcode nguồn.
- [ ] Có UI cho `insufficient_evidence`, `needs_clarification`, `ai_unavailable`, `error`.
- [ ] Đổi học phần không trộn nguồn/request.
- [ ] Test 375px / 768px / 1366px; kiểm tra `npm run build`.
- [ ] Kết nối với FastAPI qua `/api` và hoàn thành demo end-to-end.

### 15.2. Tiến Đạt — Dữ liệu

- [ ] Tạo học liệu demo có thể chia sẻ và manifest.
- [ ] Ingest từng trang, chunk ID và PDF page chính xác.
- [ ] Kiểm tra 05 trang, loại nguồn trích xuất lỗi.
- [ ] Tạo 20 câu dev gắn trang đáp án.

### 15.3. Thành Đạt — Retrieval

- [ ] Index theo `course_id`, search top-k có metadata.
- [ ] Chọn ngưỡng trên dev, ghi lại cấu hình.
- [ ] Có cả câu không đủ căn cứ và chỉ số Hit@k.

### 15.4. Khoa — AI

- [ ] Thử một lượt gọi API thực tế; nêu tên mô hình/phiên bản.
- [ ] Không gọi LLM khi thiếu nguồn.
- [ ] Prompt giới hạn nguồn; xử lý thiếu key, timeout và lỗi API.
- [ ] Không phát minh tài liệu hoặc trang trong câu trả lời.

### 15.5. Đức — Backend / tích hợp

- [ ] `/api/health`, `/api/courses`, `/api/courses/{id}/documents`, `/api/chat`.
- [ ] Pydantic schema đúng với TS type; lỗi HTTP hợp lý.
- [ ] FastAPI gọi service PDF/retrieval/LLM độc lập Streamlit.
- [ ] CORS/proxy hoạt động; thử trên máy sạch từ README.

### 15.6. Bình — QA / hồ sơ

- [ ] Giữ bộ 12 câu final độc lập; kiểm tra trang nguồn.
- [ ] Ghi test results thực tế, không chỉ tình huống thành công.
- [ ] Kiểm tra React + FastAPI trên máy khác.
- [ ] Video 02–03 phút và minh chứng kỹ thuật.
- [ ] Hỗ trợ báo cáo 03–05 trang và kiểm tra quyền truy cập.

---

## 16. NHỮNG VIỆC DUY NÊN LÀM ĐẦU TIÊN — UI-FIRST

**Trong phiên lập trình đầu tiên:**

1. Sao lưu branch Streamlit đang chạy; không xóa file gốc.
2. Khởi tạo `frontend/` bằng Vite `react-ts`, Tailwind và lucide-react.
3. Tạo `types/api.ts` theo Mục 5; gửi schema cho Đức, Khoa, Thành Đạt để xác nhận.
4. Tạo `AppShell` + sidebar + chế độ responsive, ưu tiên màn hình desktop hiện tại.
5. Tạo `ChatComposer`, `ChatMessage`, `SourceCard` bằng **mock rõ ràng trong chế độ DEV**, có đầy đủ status.
6. Tạo `services/api.ts` và test `/api/health` qua Vite proxy.
7. Thay `mockApi` bằng API thật ngay khi Đức bàn giao; kiểm tra một câu hỏi với nguồn PDF thật.
8. **Nếu chưa có nguồn thật từ FastAPI trước cuối 10/11, dừng việc đánh bóng UI và phối hợp gỡ lỗi backend.**

**Tiêu chí hoàn thành việc UI:** Người không biết code có thể chọn môn, đặt câu hỏi, thấy đang tải, đọc câu trả lời/trích đoạn, mở nguồn và hiểu ngay vì sao hệ thống không trả lời ở tình huống thiếu căn cứ.

---

## 17. NGUỒN VÀ TÀI LIỆU THAM CHIẾU

**Nguồn nội bộ dự án**

1. [Kế hoạch cuộc thi “Xây dựng ứng dụng AI” năm 2026](https://docs.google.com/document/d/1F4xvl-KJXM3B7LbNJGHVrTaFabZAZwby/edit) — thể lệ, hồ sơ và mốc thời gian.
2. [Kế hoạch UniStudy AI trên Google Docs](https://docs.google.com/document/d/1rASAqiYfQWKktoWTVboslDzTz5HwZghKvnBhOdnPVUY/edit) — phương án Hướng C ban đầu; Markdown này là bản kỹ thuật cập nhật công nghệ.
3. [Kế hoạch AI Review Analyzer ban đầu](https://docs.google.com/document/d/1G20eB61Dt4XMcjHdSICrzlTGQGW7kepYhWq0g5cWnW0/edit) — fallback đúng nếu không được đổi hướng.

**Tài liệu kỹ thuật chính thức**

4. [Vite — Getting Started](https://vite.dev/guide/) — scaffold React/TypeScript và yêu cầu Node.js.
5. [Tailwind CSS — Installation using Vite](https://tailwindcss.com/docs/installation/using-vite) — cấu hình `@tailwindcss/vite` và `@import "tailwindcss"`.
6. [FastAPI — Tutorial](https://fastapi.tiangolo.com/tutorial/) — route, schema, validation, tài liệu API.
7. [FastAPI — CORS](https://fastapi.tiangolo.com/tutorial/cors/) — cấu hình origin khi không sử dụng proxy.

---

> **Kết luận kỹ thuật:** Chọn **React + FastAPI** để có UI chuyên nghiệp và backend Python tách biệt, nhưng giá trị cần chứng minh trong cuộc thi vẫn là **hỏi đúng học phần, có căn cứ từ PDF thật, từ chối đúng khi thiếu nguồn và chạy lại được từ hồ sơ**. Không để việc đổi frontend làm mất thời gian kiểm thử cốt lõi.
