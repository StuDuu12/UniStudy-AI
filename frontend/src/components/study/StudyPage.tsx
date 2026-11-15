import { useCallback, useEffect, useState } from 'react';
import { BookOpenCheck, ChevronRight } from 'lucide-react';
import { ApiError, fetchStudyCatalog } from '../../services/api';
import type { SavedStudy, StudyCatalog, StudyState } from '../../types/study';
import { StudySession } from './StudySession';

type SavedStates = Record<string, SavedStudy | undefined>;
type OpenPdf = (docId: string, docName: string, page: number, totalPages?: number) => void;

const progressKey = (courseId: string, topicId: string) => 'unistudy.study.v1.' + courseId + '.' + topicId;

function readProgress(courseId: string, topicId: string): SavedStudy | undefined {
  try {
    const raw = localStorage.getItem(progressKey(courseId, topicId));
    const value = raw ? JSON.parse(raw) : null;
    if (typeof value?.sessionId === 'string' && (
      !value.state || ['diagnose', 'explain', 'practice', 'review'].includes(value.state.step)
    )) {
      return value;
    }
  } catch {
    // A corrupt snapshot or blocked storage should not prevent opening a lesson.
  }
}

function progressLabel(state?: StudyState): string {
  if (state?.last_result === 'independent') return 'Đã tự làm đúng';
  if (state?.last_result === 'needs_practice') return 'Cần luyện thêm';
  if (state && state.step !== 'diagnose') return 'Đang học';
  return 'Chưa bắt đầu';
}

export function StudyPage({ courseId, onOpenPdf }: { courseId: string; onOpenPdf: OpenPdf }) {
  const [catalog, setCatalog] = useState<StudyCatalog>();
  const [activeTopic, setActiveTopic] = useState<string>();
  const [progress, setProgress] = useState<SavedStates>({});
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [storageError, setStorageError] = useState(false);

  useEffect(() => {
    if (!courseId) return;
    const controller = new AbortController();
    fetchStudyCatalog(courseId, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setProgress(Object.fromEntries(result.topics.map((topic) => [topic.id, readProgress(courseId, topic.id)])));
        setCatalog(result);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof ApiError ? reason.message : 'Không thể kết nối để tải bài học.');
        }
      });
    return () => controller.abort();
  }, [courseId, reload]);

  const saveProgress = useCallback((topicId: string, snapshot: SavedStudy) => {
    setProgress((previous) => ({ ...previous, [topicId]: snapshot }));
    try {
      localStorage.setItem(progressKey(courseId, topicId), JSON.stringify(snapshot));
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }, [courseId]);

  useEffect(() => {
    if (!catalog) return;
    function sync(event: StorageEvent) {
      const item = catalog?.topics.find((topic) => progressKey(courseId, topic.id) === event.key);
      if (item) setProgress((previous) => ({ ...previous, [item.id]: readProgress(courseId, item.id) }));
    }
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, [catalog, courseId]);

  function openTopic(topicId: string) {
    function select() {
      const snapshot = readProgress(courseId, topicId) ?? progress[topicId] ?? { sessionId: crypto.randomUUID() };
      saveProgress(topicId, snapshot);
      setActiveTopic(topicId);
    }
    if (navigator.locks) {
      void navigator.locks.request(progressKey(courseId, topicId), select).catch(select);
    } else {
      select();
    }
  }

  const topic = catalog?.topics.find((item) => item.id === activeTopic);

  return (
    <section aria-label="Học cùng AI" className="flex-1 min-h-0 overflow-y-auto bg-slate-50/50">
      <div className="mx-auto w-full max-w-4xl px-4 py-5 sm:px-8 sm:py-8">
        {storageError && (
          <p role="alert" className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Trình duyệt chưa lưu được tiến độ. Bạn vẫn có thể tiếp tục trong phiên này.
          </p>
        )}
        {topic && catalog ? (
          <StudySession
            key={topic.id}
            courseId={courseId}
            topic={topic}
            initialProgress={progress[topic.id]}
            aiConfigured={catalog.ai_configured}
            onSave={saveProgress}
            onBack={() => setActiveTopic(undefined)}
            onOpenPdf={onOpenPdf}
          />
        ) : (
          <>
            <h2 className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-900">
              <BookOpenCheck aria-hidden="true" className="size-6 text-indigo-600" />
              Học cùng AI
            </h2>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-slate-600">
              Thử một câu ngắn để tìm chỗ đang vướng, đọc giải thích theo học liệu rồi tự làm một bài mới.
            </p>

            {error ? (
              <div role="alert" className="mt-5 rounded-xl border border-rose-200 bg-white p-4 text-sm text-rose-800">
                <p>{error}</p>
                <button
                  type="button"
                  className="mt-2 font-semibold underline underline-offset-2"
                  onClick={() => { setError(''); setReload((value) => value + 1); }}
                >
                  Tải lại
                </button>
              </div>
            ) : !courseId || catalog?.topics.length === 0 ? (
              <p className="mt-5 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
                Chọn Toán rời rạc hoặc Thu thập và phân tích yêu cầu để mở bài học minh họa.
              </p>
            ) : !catalog ? (
              <p role="status" className="mt-5 text-sm text-slate-600">Đang tải bài học…</p>
            ) : (
              <>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {catalog.topics.map((item) => {
                    const state = progress[item.id]?.state;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => openTopic(item.id)}
                        className="group flex min-h-32 items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-2xs transition-colors hover:border-indigo-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                      >
                        <span className="flex-1">
                          <span className="block font-semibold text-slate-900">{item.title}</span>
                          <span className="mt-1 block text-sm text-slate-600">{item.goal}</span>
                          <span className={state?.last_result === 'independent'
                            ? 'mt-3 block text-xs font-semibold text-emerald-800'
                            : 'mt-3 block text-xs font-semibold text-slate-600'}>
                            {progressLabel(state)}
                          </span>
                        </span>
                        <ChevronRight aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-slate-500 group-hover:text-indigo-600" />
                      </button>
                    );
                  })}
                </div>
                <p className="mt-4 text-xs text-slate-500">Quay lại bằng trình duyệt này để tiếp tục tiến độ đã lưu.</p>
              </>
            )}
          </>
        )}
      </div>
    </section>
  );
}
