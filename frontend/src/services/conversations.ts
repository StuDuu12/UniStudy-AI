import type { ChatStatus, Message, Source } from '../types/api';
import { deleteServerConversation, renameServerConversation, saveServerConversation } from './api';

export interface Conversation {
  id: string;
  courseId: string;
  title: string;
  titleVersion?: number;
  updatedAt: number;
  messages: Message[];
}

export interface ConversationHistory {
  selectedCourseId: string;
  activeByCourse: Record<string, string | null>;
  conversations: Conversation[];
  deletedIds: string[];
}

const STORAGE_KEY = 'unistudy.conversations.v1';
const READ_ERROR = 'Không thể đọc đầy đủ lịch sử hội thoại đã lưu trên trình duyệt.';
const WRITE_ERROR = 'Không thể lưu bản sao lịch sử trên trình duyệt.';
const SERVER_ERROR = 'Chưa lưu được lịch sử trên máy chủ. Bản trong trình duyệt vẫn được giữ.';
const STATUSES = new Set<ChatStatus>([
  'success', 'insufficient_evidence', 'needs_clarification', 'no_documents',
  'ai_unavailable', 'error', 'invalid_input',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isSource(value: unknown): value is Source {
  return isRecord(value) && typeof value.document_id === 'string'
    && typeof value.document_name === 'string' && typeof value.chunk_id === 'string'
    && typeof value.excerpt === 'string' && Number.isInteger(value.page) && Number(value.page) > 0
    && (value.score === null || typeof value.score === 'number')
    && (value.document_sha256 == null || typeof value.document_sha256 === 'string');
}

function isMessage(value: unknown): value is Message {
  return isRecord(value) && typeof value.id === 'string' && typeof value.content === 'string'
    && typeof value.timestamp === 'string' && (value.sender === 'user' || value.sender === 'assistant')
    && (value.status === undefined || STATUSES.has(value.status as ChatStatus))
    && (value.sources === undefined || (Array.isArray(value.sources) && value.sources.every(isSource)))
    && (value.message == null || typeof value.message === 'string')
    && (value.retryQuestion === undefined || typeof value.retryQuestion === 'string')
    && (value.contextQuestion === undefined || typeof value.contextQuestion === 'string')
    && (value.replyTo === undefined || typeof value.replyTo === 'string')
    && (value.createdAt === undefined || (typeof value.createdAt === 'number' && Number.isFinite(value.createdAt)));
}

function isConversation(value: unknown): value is Conversation {
  return isRecord(value) && typeof value.id === 'string' && Boolean(value.id)
    && typeof value.courseId === 'string' && Boolean(value.courseId)
    && typeof value.title === 'string' && Boolean(value.title)
    && (value.titleVersion === undefined || (Number.isSafeInteger(value.titleVersion) && Number(value.titleVersion) >= 0))
    && typeof value.updatedAt === 'number' && Number.isInteger(value.updatedAt)
    && value.updatedAt >= 0 && value.updatedAt <= 8.64e15
    && Array.isArray(value.messages) && value.messages.every(isMessage)
    && value.messages.some((message) => message.sender === 'user' && message.content.trim());
}

export function readHistory(): { history: ConversationHistory; error: string } {
  const empty: ConversationHistory = { selectedCourseId: '', activeByCourse: {}, conversations: [], deletedIds: [] };
  let raw: string | null;
  try {
    raw = globalThis.localStorage.getItem(STORAGE_KEY);
  } catch {
    return { history: empty, error: WRITE_ERROR };
  }
  if (!raw) return { history: empty, error: '' };

  try {
    const saved: unknown = JSON.parse(raw);
    if (!isRecord(saved) || !Array.isArray(saved.conversations)) {
      return { history: empty, error: READ_ERROR };
    }

    const deletedIds = Array.isArray(saved.deletedIds)
      ? saved.deletedIds.filter((id): id is string => typeof id === 'string') : [];
    const ids = new Set(deletedIds);
    const conversations = saved.conversations.map((item: unknown) => {
      if (!isRecord(item) || !Array.isArray(item.messages)) return item;
      // Older server snapshots used null for optional message fields.
      return { ...item, messages: item.messages.map((message: unknown) => isRecord(message)
        ? Object.fromEntries(Object.entries(message).filter(([, value]) => value !== null))
        : message) };
    }).filter((item): item is Conversation => {
      if (!isConversation(item) || ids.has(item.id)) return false;
      ids.add(item.id);
      return true;
    });
    const activeByCourse = isRecord(saved.activeByCourse) ? Object.fromEntries(
      Object.entries(saved.activeByCourse).filter(([courseId, id]) =>
        conversations.some((thread) => thread.id === id && thread.courseId === courseId),
      ),
    ) as ConversationHistory['activeByCourse'] : {};
    return {
      history: {
        selectedCourseId: typeof saved.selectedCourseId === 'string' ? saved.selectedCourseId : '',
        activeByCourse,
        conversations,
        deletedIds,
      },
      error: conversations.length === saved.conversations.length ? '' : READ_ERROR,
    };
  } catch {
    return { history: empty, error: READ_ERROR };
  }
}

export function mergeMessages(persisted: Message[], incoming: Message[]): Message[] {
  const byId = new Map<string, Message>();
  for (const branch of [persisted, incoming]) {
    let awaitingReply: string | undefined;
    for (const message of branch) {
      if (message.sender === 'user') {
        awaitingReply = message.id;
        if (!byId.has(message.id)) byId.set(message.id, message);
      } else {
        // Infer a link within each legacy branch before combining independently ordered turns.
        const replyTo = message.replyTo ?? awaitingReply;
        if (!byId.has(message.id)) byId.set(message.id, { ...message, replyTo });
        if (replyTo === awaitingReply) awaitingReply = undefined;
      }
    }
  }

  const ordered = [...byId.values()].sort((a, b) => (a.createdAt ?? 0) - (b.createdAt ?? 0));
  const turns: Message[] = [];
  const replies = new Map<string, Message[]>();
  for (const message of ordered) {
    if (message.sender === 'assistant' && message.replyTo && byId.get(message.replyTo)?.sender === 'user') {
      const linked = replies.get(message.replyTo) ?? [];
      linked.push(message);
      replies.set(message.replyTo, linked);
    } else {
      turns.push(message);
    }
  }
  return turns.flatMap((message) => [message, ...(replies.get(message.id) ?? [])]);
}

export function mergeConversation(persisted: Conversation, incoming: Conversation): Conversation {
  const latestTitle = (incoming.titleVersion ?? 0) > (persisted.titleVersion ?? 0) ? incoming : persisted;
  return {
    ...persisted,
    title: latestTitle.title,
    titleVersion: latestTitle.titleVersion,
    updatedAt: Math.max(persisted.updatedAt, incoming.updatedAt),
    messages: mergeMessages(persisted.messages, incoming.messages),
  };
}

let pendingWrite: Promise<unknown> = Promise.resolve();

function withHistoryLock<T>(action: () => Promise<T>): Promise<T> {
  const locks = globalThis.navigator?.locks;
  if (locks) return locks.request(STORAGE_KEY, action);
  const operation = pendingWrite.then(action);
  pendingWrite = operation.catch(() => undefined);
  return operation;
}

function writeLocal(history: ConversationHistory): string {
  try {
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    return '';
  } catch {
    return WRITE_ERROR;
  }
}

export async function saveHistory(
  history: ConversationHistory, previous: ConversationHistory, syncServer: boolean,
): Promise<{ error: string; conversations?: Conversation[]; deletedIds?: string[] }> {
  try {
    return await withHistoryLock(async () => {
      const { history: saved } = readHistory();
      const deleted = new Set([...saved.deletedIds, ...history.deletedIds]);
      const conversations = new Map(saved.conversations.map((thread) => [thread.id, thread]));
      for (const id of deleted) conversations.delete(id);
      const previousThreads = new Map(previous.conversations.map((thread) => [thread.id, thread]));
      const changed: Conversation[] = [];
      for (const thread of history.conversations) {
        if (deleted.has(thread.id)) continue;
        const persisted = conversations.get(thread.id);
        if (persisted && persisted.courseId !== thread.courseId) continue;
        const merged = persisted ? mergeConversation(persisted, thread) : thread;
        conversations.set(thread.id, merged);
        if (syncServer && previousThreads.get(thread.id) !== thread) changed.push(merged);
      }
      const activeChanges = Object.fromEntries(Object.entries(history.activeByCourse).filter(([courseId, id]) =>
        id && id !== previous.activeByCourse[courseId] && !deleted.has(id),
      ));
      const activeByCourse = Object.fromEntries(Object.entries({ ...saved.activeByCourse, ...activeChanges })
        .filter(([, id]) => id && !deleted.has(id)));
      const combined = [...conversations.values()];
      const deletedIds = [...deleted];
      const localError = writeLocal({
        selectedCourseId: history.selectedCourseId === previous.selectedCourseId
          ? saved.selectedCourseId || history.selectedCourseId : history.selectedCourseId,
        activeByCourse,
        conversations: combined,
        deletedIds,
      });
      const results = await Promise.allSettled(changed.map(saveServerConversation));
      return {
        error: localError || (results.some((result) => result.status === 'rejected') ? SERVER_ERROR : ''),
        conversations: combined,
        deletedIds,
      };
    });
  } catch {
    return { error: WRITE_ERROR };
  }
}

export function deleteHistory(id: string): Promise<string> {
  return withHistoryLock(async () => {
    await deleteServerConversation(id);
    const { history } = readHistory();
    return writeLocal({
      ...history,
      conversations: history.conversations.filter((thread) => thread.id !== id),
      activeByCourse: Object.fromEntries(Object.entries(history.activeByCourse).filter(([, active]) => active !== id)),
      deletedIds: [...new Set([...history.deletedIds, id])],
    });
  });
}

export function renameHistory(id: string, title: string): Promise<Conversation> {
  return withHistoryLock(async () => {
    const { history } = readHistory();
    if (history.deletedIds.includes(id)) throw new Error('Không tìm thấy hội thoại.');
    return renameServerConversation(id, title);
  });
}

export function conversationsForCourse(history: ConversationHistory, courseId: string): Conversation[] {
  return history.conversations.filter((thread) => thread.courseId === courseId)
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

export function activeConversation(history: ConversationHistory, courseId: string, threads: Conversation[]) {
  const activeId = Object.hasOwn(history.activeByCourse, courseId) ? history.activeByCourse[courseId] : undefined;
  if (activeId === null) return undefined;
  return threads.find((thread) => thread.id === activeId) ?? threads[0];
}

export function successfulQuestions(messages: Message[]): string[] {
  const successfulReplies = new Map<string, Message>();
  let awaitingReply: string | undefined;
  for (const message of messages) {
    if (message.sender === 'user') {
      awaitingReply = message.id;
    } else {
      const replyTo = message.replyTo ?? awaitingReply;
      if (replyTo && message.status === 'success') successfulReplies.set(replyTo, message);
      if (replyTo === awaitingReply) awaitingReply = undefined;
    }
  }

  const questions = new Map<string, string>();
  for (const message of messages) {
    const reply = successfulReplies.get(message.id);
    if (message.sender !== 'user' || !reply) continue;
    const question = reply.contextQuestion?.trim() || message.content.trim();
    if (!question) continue;
    const key = question.normalize('NFC').replace(/\s+/g, ' ').toLocaleLowerCase('vi');
    questions.delete(key);
    questions.set(key, question);
  }
  return [...questions.values()].slice(-3).map((question) => Array.from(question).slice(0, 2000).join(''));
}
