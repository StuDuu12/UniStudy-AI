export type ChatStatus =
  | 'success'
  | 'insufficient_evidence'
  | 'needs_clarification'
  | 'no_documents'
  | 'ai_unavailable'
  | 'error'
  | 'invalid_input';

export interface Source {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page: number;
  excerpt: string;
  document_sha256?: string;
  score: number | null;
}

export interface ChatRequest {
  course_id: string;
  question: string;
  previous_questions?: string[];
}

export interface ChatResponse {
  status: ChatStatus;
  answer: string;
  sources: Source[];
  message: string | null;
  context_question?: string | null;
}

export interface Course {
  course_id: string;
  course_name: string;
  document_count: number;
  status: string;
  suggested_questions?: string[];
}

export interface CourseListResponse {
  courses: Course[];
}

export interface DocumentInfo {
  document_id: string;
  document_name: string;
  page_count: number;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
}

export interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  status?: ChatStatus;
  sources?: Source[];
  message?: string | null;
  retryQuestion?: string;
  contextQuestion?: string;
  replyTo?: string;
  createdAt?: number;
  timestamp: string;
}
