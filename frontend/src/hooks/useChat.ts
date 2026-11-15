import { useState, useEffect, useRef, useCallback } from 'react';
import type { Course, DocumentInfo, Message } from '../types/api';
import {
  ApiError,
  appendCourseDocuments,
  createCourse,
  fetchCourses,
  fetchCourseDocuments,
  sendChat,
  fetchServerConversations,
} from '../services/api';
import type { ConversationHistory } from '../services/conversations';
import {
  activeConversation,
  conversationsForCourse,
  readHistory,
  saveHistory,
  deleteHistory,
  renameHistory,
  successfulQuestions,
  mergeConversation,
} from '../services/conversations';

type DocumentState = { courseId: string; documents: DocumentInfo[]; error?: string };

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && !(error instanceof TypeError) ? error.message : fallback;
}

function isConnectionError(error: unknown) {
  return error instanceof TypeError || (error instanceof ApiError && error.status >= 500);
}

function makeMessage(message: Omit<Message, 'id' | 'timestamp'>): Message {
  const now = new Date();
  return {
    ...message,
    id: crypto.randomUUID(),
    createdAt: now.getTime(),
    timestamp: now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
  };
}

export function useChat() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [documentState, setDocumentState] = useState<DocumentState | null>(null);
  const [initialHistory] = useState(readHistory);
  const [history, setHistory] = useState(initialHistory.history);
  const [historyStorageError, setHistoryStorageError] = useState(initialHistory.error);
  const historyRef = useRef(initialHistory.history);
  const [pendingConversations, setPendingConversations] = useState<Set<string>>(new Set());
  const [catalogStatus, setCatalogStatus] = useState<'loading' | 'online' | 'offline'>('loading');
  const [catalogError, setCatalogError] = useState('');
  const [catalogAttempt, setCatalogAttempt] = useState(0);

  const chatRequests = useRef(new Map<string, AbortController>());
  const documentRequest = useRef<{ courseId: string; controller: AbortController } | null>(null);
  const appendingCourses = useRef(new Set<string>());
  const selectedCourse = courses.find((course) => course.course_id === history.selectedCourseId);
  const selectedCourseId = selectedCourse?.course_id ?? '';

  const updateHistory = useCallback((
    update: (current: ConversationHistory) => ConversationHistory, persist: boolean | 'local' = true,
  ) => {
    const previous = historyRef.current;
    const next = update(previous);
    if (next === previous) return;
    historyRef.current = next;
    setHistory(next);
    if (persist) void saveHistory(next, previous, persist === true).then(({ error, conversations, deletedIds }) => {
      if (historyRef.current !== next) return;
      setHistoryStorageError(error);
      if (!conversations || !deletedIds) return;
      const merged = { ...next, conversations, deletedIds };
      historyRef.current = merged;
      setHistory(merged);
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchCourses(controller.signal).then(({ courses: items }) => {
      if (controller.signal.aborted) return;
      setCourses(items);
      updateHistory((current) => {
        if (items.some((course) => course.course_id === current.selectedCourseId)) return current;
        const preferred = (items.find((course) => course.course_id === 'tin_hoc_dai_cuong' && course.document_count > 0)
          ?? items.find((course) => course.document_count > 0) ?? items[0])?.course_id ?? '';
        return preferred === current.selectedCourseId ? current : { ...current, selectedCourseId: preferred };
      }, false);
      setCatalogStatus('online');
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setCatalogError(errorMessage(error, 'Không thể kết nối máy chủ để lấy danh sách học phần.'));
      setCatalogStatus('offline');
    });
    return () => controller.abort();
  }, [catalogAttempt, updateHistory]);

  // Sync conversation history from backend server
  useEffect(() => {
    const controller = new AbortController();
    fetchServerConversations(undefined, controller.signal).then((serverConvs) => {
      if (controller.signal.aborted || serverConvs.length === 0) return;
      updateHistory((current) => {
        const convMap = new Map(current.conversations.map((c) => [c.id, c]));
        const deleted = new Set(current.deletedIds);
        let hasChanges = false;
        for (const sConv of serverConvs) {
          if (deleted.has(sConv.id)) continue;
          const local = convMap.get(sConv.id);
          if (!local) {
            convMap.set(sConv.id, sConv);
            hasChanges = true;
          } else if (local.courseId === sConv.courseId) {
            const merged = mergeConversation(local, sConv);
            if (merged.updatedAt > local.updatedAt || merged.messages.length > local.messages.length
              || merged.titleVersion !== local.titleVersion) {
              convMap.set(sConv.id, merged);
              hasChanges = true;
            }
          }
        }
        if (!hasChanges) return current;
        return {
          ...current,
          conversations: Array.from(convMap.values()).sort((a, b) => b.updatedAt - a.updatedAt),
        };
      }, 'local');
    });
    return () => controller.abort();
  }, [updateHistory]);

  useEffect(() => {
    if (!selectedCourseId) return;
    const controller = new AbortController();
    documentRequest.current = { courseId: selectedCourseId, controller };
    fetchCourseDocuments(selectedCourseId, controller.signal).then(({ documents }) => {
      if (!controller.signal.aborted) setDocumentState({ courseId: selectedCourseId, documents });
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      if (isConnectionError(error)) setCatalogStatus('offline');
      setDocumentState({
        courseId: selectedCourseId,
        documents: [],
        error: errorMessage(error, 'Không thể kết nối máy chủ để lấy danh sách tài liệu.'),
      });
    });
    return () => controller.abort();
  }, [selectedCourseId, catalogAttempt]);

  useEffect(() => {
    const requests = chatRequests.current;
    return () => requests.forEach((controller) => controller.abort());
  }, []);

  function reloadCourses() {
    setCatalogError('');
    setCatalogStatus('loading');
    setCatalogAttempt((attempt) => attempt + 1);
  }

  function selectCourse(courseId: string) {
    if (courseId === historyRef.current.selectedCourseId) return;
    setDocumentState(null);
    updateHistory((current) => ({ ...current, selectedCourseId: courseId }));
  }

  function appendReply(conversationId: string, questionId: string, message: Omit<Message, 'id' | 'timestamp'>) {
    const reply = makeMessage({ ...message, replyTo: questionId });
    updateHistory((current) => ({
      ...current,
      conversations: current.conversations.map((thread) => {
        if (thread.id !== conversationId) return thread;
        const index = thread.messages.findIndex((item) => item.id === questionId);
        const insertion = index === -1 ? thread.messages.length : index + 1;
        return {
          ...thread,
          updatedAt: Math.max(Date.now(), thread.updatedAt + 1),
          messages: [...thread.messages.slice(0, insertion), reply, ...thread.messages.slice(insertion)],
        };
      }),
    }));
  }

  const currentDocuments = documentState?.courseId === selectedCourseId ? documentState : null;
  const canAsk = Boolean(selectedCourse?.document_count);
  const threads = conversationsForCourse(history, selectedCourseId);
  const currentThread = activeConversation(history, selectedCourseId, threads);
  const activeConversationId = currentThread?.id ?? null;

  async function sendQuestion(question: string) {
    const text = question.trim();
    const current = historyRef.current;
    if (!text || !canAsk || current.selectedCourseId !== selectedCourseId) return;
    const thread = activeConversation(current, selectedCourseId, conversationsForCourse(current, selectedCourseId));
    if (thread && chatRequests.current.has(thread.id)) return;

    const id = thread?.id ?? crypto.randomUUID();
    const controller = new AbortController();
    const previousQuestions = successfulQuestions(thread?.messages ?? []);
    const questionMessage = makeMessage({ sender: 'user', content: text });
    const updated = {
      id,
      courseId: selectedCourseId,
      title: thread?.title ?? text.replace(/\s+/g, ' '),
      titleVersion: thread?.titleVersion,
      updatedAt: Math.max(Date.now(), (thread?.updatedAt ?? 0) + 1),
      messages: [...(thread?.messages ?? []), questionMessage],
    };
    chatRequests.current.set(id, controller);
    setPendingConversations((previous) => new Set(previous).add(id));
    updateHistory((previous) => ({
      ...previous,
      activeByCourse: { ...previous.activeByCourse, [selectedCourseId]: id },
      conversations: [updated, ...previous.conversations.filter((item) => item.id !== id)],
    }));

    try {
      const response = await sendChat({
        course_id: selectedCourseId,
        question: text,
        ...(previousQuestions.length > 0 ? { previous_questions: previousQuestions } : {}),
      }, controller.signal);
      if (controller.signal.aborted) return;
      setCatalogStatus('online');
      appendReply(id, questionMessage.id, {
        sender: 'assistant',
        content: response.answer,
        status: response.status,
        sources: response.sources,
        message: response.message,
        contextQuestion: response.context_question ?? undefined,
        retryQuestion: response.status === 'error' || response.status === 'ai_unavailable' ? text : undefined,
      });
    } catch (error) {
      if (controller.signal.aborted) return;
      if (isConnectionError(error)) setCatalogStatus('offline');
      appendReply(id, questionMessage.id, {
        sender: 'assistant', content: '', status: 'error', retryQuestion: text,
        message: errorMessage(error, 'Không thể kết nối đến máy chủ. Vui lòng thử lại.'),
      });
    } finally {
      chatRequests.current.delete(id);
      if (!controller.signal.aborted) setPendingConversations((previous) => {
        const next = new Set(previous);
        next.delete(id);
        return next;
      });
    }
  }

  async function addCourse(name: string, files: File[]) {
    try {
      const course = await createCourse(name, files);
      setCourses((previous) => [...previous, course]);
      selectCourse(course.course_id);
    } catch (error) {
      if (isConnectionError(error)) setCatalogStatus('offline');
      throw error;
    }
  }

  async function addDocuments(courseId: string, files: File[]) {
    if (appendingCourses.current.has(courseId)) throw new Error('Học phần đang tải PDF. Hãy đợi lượt tải hiện tại hoàn tất.');
    appendingCourses.current.add(courseId);
    try {
      const { documents } = await appendCourseDocuments(courseId, files);
      setCourses((previous) => previous.map((course) => course.course_id === courseId
        ? { ...course, document_count: documents.length }
        : course));
      const request = documentRequest.current;
      if (request?.courseId === courseId) {
        request.controller.abort();
        setDocumentState({ courseId, documents });
      }
    } catch (error) {
      if (isConnectionError(error)) setCatalogStatus('offline');
      throw error;
    } finally {
      appendingCourses.current.delete(courseId);
    }
  }

  function newConversation() {
    if (!selectedCourseId) return;
    updateHistory((current) => ({
      ...current, activeByCourse: { ...current.activeByCourse, [selectedCourseId]: null },
    }), false);
  }

  function selectConversation(id: string) {
    updateHistory((current) => {
      if (!current.conversations.some((thread) => thread.id === id && thread.courseId === current.selectedCourseId)) {
        return current;
      }
      return { ...current, activeByCourse: { ...current.activeByCourse, [current.selectedCourseId]: id } };
    });
  }

  async function deleteConversation(id: string) {
    chatRequests.current.get(id)?.abort();
    setPendingConversations((previous) => {
      const next = new Set(previous);
      next.delete(id);
      return next;
    });
    try {
      const error = await deleteHistory(id);
      updateHistory((current) => ({
        ...current,
        activeByCourse: Object.fromEntries(Object.entries(current.activeByCourse)
          .map(([courseId, active]) => [courseId, active === id ? null : active])),
        conversations: current.conversations.filter((thread) => thread.id !== id),
        deletedIds: [...new Set([...current.deletedIds, id])],
      }), false);
      setHistoryStorageError(error);
    } catch (error) {
      setHistoryStorageError(errorMessage(error, 'Không thể kết nối máy chủ để xóa hội thoại.'));
    }
  }

  async function renameConversation(id: string, title: string) {
    if (!historyRef.current.conversations.some((thread) => thread.id === id)) {
      throw new Error('Không tìm thấy hội thoại.');
    }
    const renamed = await renameHistory(id, title);
    updateHistory((current) => ({
      ...current,
      conversations: current.conversations.map((item) => item.id === id ? mergeConversation(item, renamed) : item),
    }), 'local');
  }

  return {
    courses,
    selectedCourseId,
    selectedCourse,
    documents: currentDocuments?.documents ?? [],
    documentsLoading: Boolean(selectedCourseId) && currentDocuments === null,
    documentsError: currentDocuments?.error,
    messages: currentThread?.messages ?? [],
    conversations: threads.map(({ id, title, updatedAt }) => ({ id, title, updatedAt })),
    activeConversationId,
    historyStorageError,
    loading: activeConversationId !== null && pendingConversations.has(activeConversationId),
    canAsk,
    catalogStatus,
    catalogError,
    onReloadCourses: reloadCourses,
    onSelectCourse: selectCourse,
    onNewConversation: newConversation,
    onSelectConversation: selectConversation,
    onDeleteConversation: deleteConversation,
    onRenameConversation: renameConversation,
    onSendQuestion: sendQuestion,
    onAddCourse: addCourse,
    onAddDocuments: addDocuments,
  };
}
