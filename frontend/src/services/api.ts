import type {
  ChatRequest,
  ChatResponse,
  Course,
  CourseListResponse,
  DocumentListResponse,
  Message,
  Source,
} from '../types/api';
import type { Conversation } from './conversations';

const API_BASE = '/api';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function fetchCourses(signal?: AbortSignal): Promise<CourseListResponse> {
  const response = await fetch(`${API_BASE}/courses`, { signal });
  return readResponse<CourseListResponse>(response, 'Không thể lấy danh sách học phần');
}

export async function fetchCourseDocuments(
  courseId: string,
  signal?: AbortSignal
): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/documents`, { signal });
  return readResponse<DocumentListResponse>(response, 'Không thể lấy danh sách tài liệu');
}

export async function fetchDocumentInfo(
  documentId: string,
  signal?: AbortSignal
): Promise<{ document_id: string; document_name: string; page_count: number }> {
  const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(documentId)}/info`, { signal });
  return readResponse(response, 'Không thể lấy thông tin tài liệu');
}

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

  return readResponse<ChatResponse>(response, 'Không thể gửi câu hỏi');
}

async function readResponse<T>(response: Response, failure: string): Promise<T> {
  if (response.ok) return response.json();
  const error = await response.json().catch(() => null);
  const detail = typeof error?.detail === 'string' ? error.detail : `${failure} (HTTP ${response.status}).`;
  throw new ApiError(detail, response.status);
}

export async function createCourse(courseName: string, files: File[]): Promise<Course> {
  const body = new FormData();
  body.set('course_name', courseName);
  for (const file of files) body.append('files', file);
  const response = await fetch(`${API_BASE}/courses`, { method: 'POST', body });
  return readResponse<Course>(response, 'Không thể tạo học phần');
}

export async function renameCourse(courseId: string, courseName: string): Promise<Course> {
  const response = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ course_name: courseName }),
  });
  return readResponse<Course>(response, 'Không thể đổi tên học phần');
}

export async function deleteCourse(courseId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}`, { method: 'DELETE' });
  if (!response.ok) await readResponse(response, 'Không thể xóa học phần');
}

export async function appendCourseDocuments(courseId: string, files: File[]): Promise<DocumentListResponse> {
  const body = new FormData();
  for (const file of files) body.append('files', file);
  const response = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/documents`, {
    method: 'POST', body,
  });
  return readResponse<DocumentListResponse>(response, 'Không thể thêm PDF');
}

export function getDocumentPdfUrl(documentId: string, page?: number): string {
  const base = `${API_BASE}/documents/${encodeURIComponent(documentId)}`;
  return page ? `${base}#page=${page}` : base;
}

export function getDocumentSinglePagePdfUrl(documentId: string, page: number): string {
  return `${API_BASE}/documents/${encodeURIComponent(documentId)}/page/${page}/pdf`;
}

export function getDocumentPagePreviewUrl(documentId: string, page: number, digest?: string): string {
  const url = `${API_BASE}/documents/${encodeURIComponent(documentId)}/page/${page}`;
  return digest ? `${url}?sha256=${encodeURIComponent(digest)}` : url;
}

export async function fetchFormattedExcerpt(source: Source, signal: AbortSignal): Promise<string> {
  const params = new URLSearchParams({ chunk_id: source.chunk_id, sha256: source.document_sha256 ?? '' });
  const path = `${API_BASE}/documents/${encodeURIComponent(source.document_id)}/page/${source.page}/excerpt`;
  const response = await fetch(`${path}?${params}`, { signal });
  const { markdown } = await readResponse<{ markdown: string }>(response, 'Không thể lấy đoạn trích');
  return markdown;
}

export function getDocumentDownloadUrl(documentId: string): string {
  return `${API_BASE}/documents/${encodeURIComponent(documentId)}`;
}

interface ServerMessage {
  id: string;
  sender: Message['sender'];
  content: string;
  timestamp: string;
  status: Message['status'] | null;
  sources: Message['sources'] | null;
  message: string | null;
  context_question: string | null;
  retry_question: string | null;
  reply_to: string | null;
  created_at: number | null;
}

interface ServerConversation {
  id: string;
  course_id: string;
  title: string;
  updated_at: number;
  messages: ServerMessage[];
}

export async function fetchServerConversations(
  courseId?: string,
  signal?: AbortSignal
): Promise<Conversation[]> {
  const url = courseId
    ? `${API_BASE}/conversations?course_id=${encodeURIComponent(courseId)}`
    : `${API_BASE}/conversations`;
  try {
    const res = await fetch(url, { signal });
    if (!res.ok) return [];
    const data = await res.json() as { conversations: ServerConversation[] };
    if (!Array.isArray(data?.conversations)) return [];
    return data.conversations.map((item) => ({
      id: item.id,
      courseId: item.course_id,
      title: item.title,
      updatedAt: item.updated_at,
      messages: item.messages.map((m) => ({
        id: m.id,
        sender: m.sender,
        content: m.content,
        timestamp: m.timestamp,
        status: m.status ?? undefined,
        sources: m.sources ?? undefined,
        message: m.message,
        contextQuestion: m.context_question ?? undefined,
        retryQuestion: m.retry_question ?? undefined,
        replyTo: m.reply_to ?? undefined,
        createdAt: m.created_at ?? undefined,
      })),
    }));
  } catch {
    return [];
  }
}

export async function saveServerConversation(
  conversation: Conversation
): Promise<void> {
  const payload = {
      id: conversation.id,
      course_id: conversation.courseId,
      title: conversation.title,
      updated_at: conversation.updatedAt,
      messages: conversation.messages.map((m) => ({
        id: m.id,
        sender: m.sender,
        content: m.content,
        timestamp: m.timestamp,
        status: m.status,
        sources: m.sources,
        message: m.message,
        context_question: m.contextQuestion,
        retry_question: m.retryQuestion,
        reply_to: m.replyTo,
        created_at: m.createdAt,
      })),
  };
  const response = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) await readResponse(response, 'Không thể lưu hội thoại');
}

export async function deleteServerConversation(
  conversationId: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok && response.status !== 404) await readResponse(response, 'Không thể xóa hội thoại');
}

export async function renameServerConversation(
  id: string,
  title: string
): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
