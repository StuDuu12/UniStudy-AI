import React, { useId, useRef, useState } from 'react';
import { Check, FolderOpen, GraduationCap, History, MessageSquare, Pencil, PlusCircle, Trash2, X } from 'lucide-react';
import type { Course, DocumentInfo } from '../../types/api';
import { CourseSelector } from '../courses/CourseSelector';
import { DocumentList } from '../courses/DocumentList';
import { CourseUploadForm } from '../courses/CourseUploadForm';

interface AppSidebarProps {
  courses: Course[];
  selectedCourseId: string;
  documents: DocumentInfo[];
  documentsLoading?: boolean;
  documentsError?: string;
  catalogStatus: 'loading' | 'online' | 'offline';
  catalogError: string;
  conversations: ReadonlyArray<{ id: string; title: string; updatedAt: number }>;
  activeConversationId: string | null;
  historyStorageError: string;
  isOpen: boolean;
  onClose: () => void;
  onSelectCourse: (courseId: string) => void;
  onReloadCourses: () => void;
  onAddCourse: (name: string, files: File[]) => Promise<void>;
  onAddDocuments: (courseId: string, files: File[]) => Promise<void>;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation?: (id: string) => void;
  onRenameConversation: (id: string, title: string) => Promise<void>;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

interface RenameEditor {
  id: string;
  courseId: string;
  value: string;
  saving?: boolean;
  error?: string;
}

const MAX_TITLE_LENGTH = 200;
const dateFormat = new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
const timeFormat = new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit' });

function conversationTime(updatedAt: number): string {
  const date = new Date(updatedAt);
  if (!Number.isFinite(date.getTime())) return '';
  return `${dateFormat.format(date)} · ${timeFormat.format(date)}`;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  courses,
  selectedCourseId,
  documents,
  documentsLoading,
  documentsError,
  catalogStatus,
  catalogError,
  conversations,
  activeConversationId,
  historyStorageError,
  isOpen,
  onClose,
  onSelectCourse,
  onReloadCourses,
  onAddCourse,
  onAddDocuments,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onOpenPdfViewer,
}) => {
  const [renameEditor, setRenameEditor] = useState<RenameEditor | null>(null);
  const renameErrorId = useId();
  const restoreRenameFocus = useRef<string | null>(null);

  if (renameEditor && renameEditor.courseId !== selectedCourseId) setRenameEditor(null);

  function closeRename(id: string) {
    restoreRenameFocus.current = id;
    setRenameEditor(null);
  }

  async function saveRename(event: React.FormEvent<HTMLFormElement>, editor: RenameEditor) {
    event.preventDefault();
    if (editor.saving) return;
    const title = editor.value.trim();
    if (!title || Array.from(title).length > MAX_TITLE_LENGTH) {
      setRenameEditor({ ...editor, error: `Tên hội thoại cần từ 1 đến ${MAX_TITLE_LENGTH} ký tự.` });
      return;
    }

    const form = event.currentTarget;
    setRenameEditor({ ...editor, saving: true, error: undefined });
    try {
      await onRenameConversation(editor.id, title);
      if (form.isConnected) closeRename(editor.id);
    } catch (error) {
      if (form.isConnected) {
        const message = error instanceof Error && !(error instanceof TypeError) && error.message
          ? error.message
          : 'Không thể đổi tên hội thoại. Vui lòng thử lại.';
        setRenameEditor({ ...editor, error: message });
      }
    }
  }

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-30 bg-slate-900/45 lg:hidden"
        />
      )}

      {/* Sidebar container */}
      <aside
        id="study-sidebar"
        aria-label="Điều hướng học phần và hội thoại"
        className={`fixed inset-y-0 left-0 z-40 flex w-80 max-w-[calc(100%-3rem)] shrink-0 flex-col border-r border-slate-200/80 bg-white shadow-lg transition-transform duration-200 motion-reduce:transition-none lg:static lg:max-w-none lg:shadow-none ${
          isOpen ? 'visible translate-x-0' : 'invisible -translate-x-full lg:visible lg:translate-x-0'
        }`}
      >
        <div className="shrink-0 border-b border-slate-200/80 px-4 py-3.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow-xs">
                <GraduationCap aria-hidden="true" className="size-5" />
              </div>
              <div className="min-w-0">
                <span className="block text-base leading-5 font-bold tracking-tight text-slate-900">UniStudy AI</span>
                <p className="mt-0.5 text-xs leading-4 text-slate-600">Trợ lý học tập đại học</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Đóng menu"
              className="grid size-9 shrink-0 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-indigo-500 lg:hidden"
            >
              <X aria-hidden="true" className="size-5" />
            </button>
          </div>

          <button
            type="button"
            onClick={onNewConversation}
            disabled={!selectedCourseId}
            className="mt-3 flex w-full cursor-pointer items-center gap-2.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2.5 text-left text-sm font-semibold text-indigo-800 transition-colors hover:bg-indigo-100 focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PlusCircle aria-hidden="true" className="size-4 shrink-0" />
            <span>Hội thoại mới</span>
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain px-4 py-3.5">
          <section aria-label="Học phần" className="space-y-2">
            <CourseSelector courses={courses} selectedCourseId={selectedCourseId} onSelect={onSelectCourse} />
            {catalogStatus === 'loading' && (
              <p role="status" className="text-xs text-slate-600">Đang tải học phần…</p>
            )}
            {catalogStatus === 'offline' && (
              <div className="space-y-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
                <p role="alert">{catalogError || 'Không thể kết nối máy chủ.'}</p>
                <button type="button" onClick={onReloadCourses} className="rounded-md font-semibold underline focus-visible:ring-2 focus-visible:ring-indigo-500">
                  Tải lại danh sách học phần
                </button>
              </div>
            )}
            <CourseUploadForm create disabled={catalogStatus !== 'online'} onUpload={onAddCourse} />
          </section>

          {selectedCourseId && (
            <section aria-labelledby="conversation-history-title" className="space-y-2 border-t border-slate-200/80 pt-3">
              <div className="flex items-center justify-between gap-2">
                <h2 id="conversation-history-title" className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <History aria-hidden="true" className="size-4 text-slate-600" />
                  Lịch sử hội thoại
                </h2>
                <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs tabular-nums text-slate-600">{conversations.length} cuộc</span>
              </div>
              {historyStorageError && <p role="status" className="text-xs text-amber-800">{historyStorageError}</p>}
              {conversations.length === 0 ? (
                <p className="rounded-lg bg-slate-50 px-3 py-3 text-sm leading-5 text-slate-600">Chưa có hội thoại trong học phần này.</p>
              ) : (
                <ul className="max-h-60 space-y-1 overflow-y-auto pr-1">
                  {conversations.map(({ id, title, updatedAt }) => {
                    const active = id === activeConversationId;
                    if (renameEditor?.id === id) {
                      return (
                        <li key={id} className={`rounded-lg p-1.5 ${active ? 'bg-indigo-50' : 'bg-slate-50'}`}>
                          <form
                            aria-busy={renameEditor.saving}
                            className="space-y-1"
                            onSubmit={(event) => void saveRename(event, renameEditor)}
                          >
                            <div className="flex items-center gap-1">
                              <input
                                autoFocus
                                aria-label="Tên hội thoại"
                                aria-describedby={renameEditor.error ? renameErrorId : undefined}
                                type="text"
                                value={renameEditor.value}
                                readOnly={renameEditor.saving}
                                onChange={(event) => setRenameEditor({ id, courseId: selectedCourseId, value: event.target.value })}
                                onKeyDown={(event) => {
                                  if (event.key === 'Escape' && !event.nativeEvent.isComposing && !renameEditor.saving) {
                                    event.preventDefault();
                                    closeRename(id);
                                  }
                                }}
                                className="min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-base text-slate-900 focus-visible:ring-2 focus-visible:ring-indigo-500 lg:text-sm"
                              />
                              <button
                                type="submit"
                                title="Lưu tên hội thoại"
                                aria-label="Lưu tên hội thoại"
                                disabled={renameEditor.saving}
                                className="grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-indigo-700 hover:bg-white focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50"
                              >
                                <Check aria-hidden="true" className="size-4" />
                              </button>
                              <button
                                type="button"
                                title="Hủy đổi tên"
                                aria-label="Hủy đổi tên"
                                disabled={renameEditor.saving}
                                onClick={() => closeRename(id)}
                                className="grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-slate-600 hover:bg-white focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50"
                              >
                                <X aria-hidden="true" className="size-4" />
                              </button>
                            </div>
                            {renameEditor.error && (
                              <p id={renameErrorId} role="alert" className="px-1 text-xs text-rose-800">{renameEditor.error}</p>
                            )}
                          </form>
                        </li>
                      );
                    }

                    return (
                      <li key={id} className={`group relative flex items-center rounded-lg ${active ? 'bg-indigo-50' : 'hover:bg-slate-50'}`}>
                        {active && <span aria-hidden="true" className="pointer-events-none absolute inset-y-3 left-0 w-0.5 rounded-full bg-indigo-600" />}
                        <button
                          type="button"
                          title={title}
                          aria-current={active ? 'true' : undefined}
                          onClick={() => onSelectConversation(id)}
                          className={`flex min-w-0 flex-1 cursor-pointer items-start gap-2.5 rounded-lg px-3 py-1.5 text-left focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500 ${active ? 'text-indigo-900' : 'text-slate-800'}`}
                        >
                          <MessageSquare aria-hidden="true" className={`mt-0.5 size-4 shrink-0 ${active ? 'text-indigo-600' : 'text-slate-500'}`} />
                          <span className="min-w-0 flex-1">
                            <span className={`line-clamp-2 text-sm leading-4.5 wrap-anywhere ${active ? 'font-semibold' : 'font-medium'}`}>{title}</span>
                            <span className="mt-0.5 block text-xs leading-4 text-slate-600">{conversationTime(updatedAt)}</span>
                          </span>
                        </button>
                        <button
                          ref={(button) => {
                            if (button && restoreRenameFocus.current === id) {
                              restoreRenameFocus.current = null;
                              button.focus();
                            }
                          }}
                          type="button"
                          title="Đổi tên hội thoại"
                          aria-label={`Đổi tên hội thoại ${title}`}
                          disabled={renameEditor?.saving}
                          onClick={() => setRenameEditor({ id, courseId: selectedCourseId, value: title })}
                          className="grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-slate-600 transition-opacity hover:bg-white hover:text-indigo-600 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"
                        >
                          <Pencil aria-hidden="true" className="size-4" />
                        </button>
                        {onDeleteConversation && (
                          <button
                            type="button"
                            title="Xóa cuộc hội thoại này"
                            aria-label={`Xóa hội thoại ${title}`}
                            onClick={() => onDeleteConversation(id)}
                            className="mr-1 grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-slate-600 transition-opacity hover:bg-white hover:text-red-700 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-indigo-500 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"
                          >
                            <Trash2 aria-hidden="true" className="size-4" />
                          </button>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          )}

          {selectedCourseId && (
            <section aria-label="Học liệu của học phần" className="space-y-1 border-t border-slate-200/80 pt-3">
              <div className="flex items-center justify-between gap-2">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <FolderOpen aria-hidden="true" className="size-4 text-slate-600" />
                  Học liệu đã nạp
                </h2>
                <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs tabular-nums text-slate-600">
                  {documents.length} tệp
                </span>
              </div>
              <CourseUploadForm
                key={selectedCourseId}
                disabled={catalogStatus !== 'online'}
                onUpload={(_, files) => onAddDocuments(selectedCourseId, files)}
              />
              <DocumentList
                documents={documents}
                loading={documentsLoading}
                error={documentsError}
                onOpenPdfViewer={onOpenPdfViewer}
              />
            </section>
          )}
        </div>

        <div className="flex shrink-0 flex-wrap items-center justify-between gap-x-2 gap-y-1 border-t border-slate-200/80 bg-slate-50 px-4 py-3 text-xs text-slate-600">
          <span className="font-medium">K73E1 · Đội 1</span>
          <span>Cuộc thi AI 2026</span>
        </div>
      </aside>
    </>
  );
};
