import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, BookOpen, Lightbulb, Sparkles } from 'lucide-react';
import { ApiError, sendStudyTurn } from '../../services/api';
import type { Source } from '../../types/api';
import type { SavedStudy, StudyAction, StudyStep, StudyTopic, StudyTurn } from '../../types/study';
import { AnswerMarkdown } from '../shared/AnswerMarkdown';

interface StudySessionProps {
  courseId: string;
  topic: StudyTopic;
  initialProgress?: SavedStudy;
  aiConfigured: boolean;
  onSave: (topicId: string, snapshot: SavedStudy) => void;
  onBack: () => void;
  onOpenPdf: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

const STEPS: Record<StudyStep, string> = {
  diagnose: 'Kiểm tra ban đầu',
  explain: 'Giải thích',
  practice: 'Tự làm',
  review: 'Kết quả',
};
const primaryButton = 'min-h-10 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50';
const secondaryButton = 'inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-indigo-300 hover:text-indigo-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50';

export function StudySession({ courseId, topic, initialProgress, aiConfigured, onSave, onBack, onOpenPdf }: StudySessionProps) {
  const [savedProgress] = useState(() => initialProgress ?? { sessionId: crypto.randomUUID() });
  const [turn, setTurn] = useState<StudyTurn>();
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [activeAction, setActiveAction] = useState<StudyAction>();
  const [reload, setReload] = useState(0);
  const [recovered, setRecovered] = useState(false);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        let view;
        try {
          view = await sendStudyTurn(
            courseId, topic.id, { action: 'open', session_id: savedProgress.sessionId }, controller.signal,
          );
          if (savedProgress.state && savedProgress.state.step !== 'diagnose' && view.state.step === 'diagnose'
            && !controller.signal.aborted) setRecovered(true);
        } catch (reason) {
          if (controller.signal.aborted || !(reason instanceof ApiError)
            || ![404, 422].includes(reason.status)) throw reason;
          const newSession = crypto.randomUUID();
          onSave(topic.id, { sessionId: newSession });
          view = await sendStudyTurn(courseId, topic.id, { action: 'open', session_id: newSession }, controller.signal);
          if (!controller.signal.aborted) setRecovered(true);
        }
        if (!controller.signal.aborted) {
          if (view.session_id) onSave(topic.id, { sessionId: view.session_id, state: view.state });
          setTurn(view);
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          setError(reason instanceof ApiError ? reason.message : 'Không thể kết nối để mở bài học.');
        }
      }
    }
    void load();
    return () => {
      controller.abort();
      pending.current?.abort();
      pending.current = null;
    };
  }, [courseId, topic.id, savedProgress, reload, onSave]);

  async function advance(action: StudyAction) {
    if (!turn) return;
    if (pending.current) {
      if (activeAction !== 'ai' || action !== 'practice') return;
      pending.current.abort();
    }
    const controller = new AbortController();
    pending.current = controller;
    setActiveAction(action);
    setError('');
    try {
      const next = await sendStudyTurn(courseId, topic.id, {
        action,
        session_id: turn.session_id,
        revision: turn.revision,
        answer: action === 'submit' ? answer : undefined,
      }, controller.signal);
      if (controller.signal.aborted) return;
      setTurn(next);
      if (next.state.step !== turn.state.step || action === 'submit') setAnswer('');
      if (next.session_id && action !== 'ai') {
        onSave(topic.id, { sessionId: next.session_id, state: next.state });
        setRecovered(false);
      }
    } catch (reason) {
      if (!controller.signal.aborted) {
        setError(reason instanceof ApiError ? reason.message : 'Mất kết nối. Hãy thử lại khi mạng ổn định.');
        if (reason instanceof ApiError && reason.status === 409 && turn.session_id) {
          const fresh = await sendStudyTurn(
            courseId, topic.id, { action: 'view', session_id: turn.session_id }, controller.signal,
          ).catch(() => undefined);
          if (fresh?.session_id && !controller.signal.aborted) {
            setTurn(fresh);
            if (fresh.revision !== turn.revision) setAnswer('');
            onSave(topic.id, { sessionId: fresh.session_id, state: fresh.state });
          }
        }
      }
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setActiveAction(undefined);
      }
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (answer.trim()) void advance('submit');
  }

  function sourceButton(source: Source, label: string) {
    return (
      <button
        key={source.chunk_id}
        type="button"
        onClick={() => onOpenPdf(source.document_id, source.document_name, source.page)}
        className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-left text-xs font-semibold text-emerald-900 hover:bg-emerald-100"
      >
        <BookOpen aria-hidden="true" className="size-4 shrink-0" />
        {label}
      </button>
    );
  }

  const step = turn?.state.step;
  const busy = activeAction !== undefined;
  const source = turn?.sources[0];

  return (
    <>
      <button type="button" onClick={onBack} className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-700 hover:underline">
        <ArrowLeft aria-hidden="true" className="size-4" /> Các bài học
      </button>
      <h2 className="mt-2 text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">{topic.title}</h2>
      {step && (
        <ol aria-label="Các bước học" className="mt-4 flex flex-wrap gap-2 text-xs">
          {Object.entries(STEPS).map(([key, label]) => (
            <li
              key={key}
              aria-current={key === step ? 'step' : undefined}
              className={key === step
                ? 'rounded-md bg-indigo-100 px-2.5 py-1.5 font-semibold text-indigo-900'
                : 'rounded-md bg-slate-100 px-2.5 py-1.5 text-slate-600'}
            >
              {label}
            </li>
          ))}
        </ol>
      )}

      <div className="mt-4 space-y-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-800 shadow-2xs sm:p-6">
        {recovered && <p role="status" className="text-amber-800">Tiến độ cũ không đọc được. Bài học đã mở lại từ đầu.</p>}
        {error && (
          <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-rose-900">
            {error}
            {!turn && (
              <button
                type="button"
                className="ml-2 font-semibold underline underline-offset-2"
                onClick={() => { setError(''); setReload((value) => value + 1); }}
              >
                Thử lại
              </button>
            )}
          </div>
        )}
        {!turn && !error && <p role="status" className="text-slate-600">Đang mở bài học…</p>}

        {turn && step === 'review' && (
          <h3 className={turn.state.last_result === 'independent' ? 'font-semibold text-emerald-800' : 'font-semibold text-amber-900'}>
            {turn.state.last_result === 'independent' ? 'Đã tự làm đúng' : 'Cần luyện thêm'}
          </h3>
        )}
        {turn?.feedback && (
          <p role="status" className="rounded-lg border border-sky-200 bg-sky-50 p-3 leading-relaxed text-sky-950">
            {turn.feedback}
          </p>
        )}
        {turn?.hint && (
          <p role="status" className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 leading-relaxed text-amber-950">
            <Lightbulb aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <span>{turn.hint}</span>
          </p>
        )}
        {turn?.lesson && <AnswerMarkdown text={turn.lesson} />}
        {source && sourceButton(source, topic.title + ' · Trang PDF ' + source.page)}

        {turn?.ai_answer && (
          <section aria-label="Giải thích thêm của AI" className="space-y-3 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
            <h3 className="font-semibold text-indigo-950">Giải thích thêm của AI</h3>
            <AnswerMarkdown text={turn.ai_answer} disableLinksAndImages />
            <div className="flex flex-wrap gap-2">
              {turn.ai_sources.map((item, index) => sourceButton(item, '[' + (index + 1) + '] Trang PDF ' + item.page))}
            </div>
          </section>
        )}
        {turn?.ai_message && <p role="status" className="text-amber-900">{turn.ai_message}</p>}

        {turn?.prompt && (
          <form onSubmit={submit} className="space-y-3">
            <p id="study-prompt" className="text-base font-medium leading-relaxed text-slate-900">{turn.prompt}</p>
            <label htmlFor="study-answer" className="block font-medium">Câu trả lời của bạn</label>
            <input
              autoComplete="off"
              id="study-answer"
              aria-describedby="study-prompt study-format"
              type="text"
              maxLength={120}
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              disabled={busy}
              className="min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2 text-base text-slate-900 focus:border-indigo-600 focus:outline-2 focus:outline-indigo-600/30"
            />
            <p id="study-format" className="text-xs text-slate-600">Ngăn cách các số nguyên bằng dấu phẩy hoặc khoảng trắng.</p>
            <div className="flex flex-wrap gap-2">
              <button className={primaryButton} type="submit" disabled={busy || !answer.trim()}>Kiểm tra câu trả lời</button>
              {step === 'diagnose' && (
                <button className={secondaryButton} type="button" disabled={busy} onClick={() => void advance('explain')}>
                  Xem giải thích trước
                </button>
              )}
              {step === 'practice' && turn.state.hint_level < 2 && (
                <button className={secondaryButton} type="button" disabled={busy} onClick={() => void advance('hint')}>
                  {turn.state.hint_level ? 'Gợi ý tiếp theo' : 'Xem gợi ý'}
                </button>
              )}
              {step === 'practice' && (turn.state.practice_mistake || turn.state.hint_level === 2) && (
                <button className={secondaryButton} type="button" disabled={busy} onClick={() => void advance('solution')}>
                  Xem lời giải
                </button>
              )}
            </div>
          </form>
        )}
        {step === 'explain' && (
          <div className="flex flex-wrap items-center gap-2">
            <button className={primaryButton} type="button" disabled={busy && activeAction !== 'ai'} onClick={() => void advance('practice')}>Tự làm bài mới</button>
            {aiConfigured ? (
              <button className={secondaryButton} type="button" disabled={busy} onClick={() => void advance('ai')}>
                <Sparkles aria-hidden="true" className="size-4" /> Giải thích thêm với AI
              </button>
            ) : (
              <p className="text-xs text-slate-500">Giải thích thêm với AI cần cấu hình mô hình trên máy chủ.</p>
            )}
          </div>
        )}
        {step === 'review' && (
          <button className={primaryButton} type="button" disabled={busy} onClick={() => void advance('retry')}>Ôn với dữ kiện khác</button>
        )}
        {busy && <p role="status" className="text-slate-600">{activeAction === 'ai' ? 'Đang tạo giải thích từ học liệu…' : 'Đang xử lý…'}</p>}
      </div>
    </>
  );
}
