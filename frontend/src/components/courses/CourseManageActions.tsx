import { useId, useRef, useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';

interface CourseManageActionsProps {
  courseName: string;
  disabled: boolean;
  pending: boolean;
  onPendingChange: (pending: boolean) => void;
  onRename: (name: string) => Promise<void>;
  onDelete: () => Promise<void>;
}

const secondaryButton = 'inline-flex min-h-9 cursor-pointer items-center justify-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-50';
const actionButton = 'min-h-9 cursor-pointer rounded-lg px-2.5 py-1.5 text-xs font-semibold text-white focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50';

export function CourseManageActions({ courseName, disabled, pending, onPendingChange, onRename, onDelete }: CourseManageActionsProps) {
  const panelId = useId();
  const editButton = useRef<HTMLButtonElement>(null);
  const deleteButton = useRef<HTMLButtonElement>(null);
  const [mode, setMode] = useState<'rename' | 'delete' | null>(null);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const canRename = Boolean(name.trim()) && name.trim() !== courseName;

  function open(nextMode: 'rename' | 'delete') {
    setName(courseName);
    setError('');
    setMode(nextMode);
  }

  function cancel() {
    setMode(null);
    setError('');
    (mode === 'rename' ? editButton : deleteButton).current?.focus();
  }

  async function submit() {
    if (pending || disabled || !mode || (mode === 'rename' && !canRename)) return;
    onPendingChange(true);
    setError('');
    try {
      if (mode === 'rename') await onRename(name.trim());
      else await onDelete();
      setMode(null);
    } catch (cause) {
      const fallback = mode === 'rename' ? 'Không thể đổi tên học phần. Hãy thử lại.' : 'Không thể xóa học phần. Hãy thử lại.';
      setError(cause instanceof Error && !(cause instanceof TypeError) ? cause.message : fallback);
    } finally {
      onPendingChange(false);
    }
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <button type="button" ref={editButton} disabled={disabled || pending} onClick={() => open('rename')}
          aria-expanded={mode === 'rename'} aria-controls={mode === 'rename' ? panelId : undefined}
          className={`${secondaryButton} border-slate-200 text-slate-700 hover:bg-indigo-50 hover:text-indigo-900`}>
          <Pencil aria-hidden="true" className="size-3.5 shrink-0" /> Đổi tên học phần
        </button>
        <button type="button" ref={deleteButton} disabled={disabled || pending} onClick={() => open('delete')}
          aria-expanded={mode === 'delete'} aria-controls={mode === 'delete' ? panelId : undefined}
          className={`${secondaryButton} border-rose-200 text-rose-700 hover:bg-rose-50`}>
          <Trash2 aria-hidden="true" className="size-3.5 shrink-0" /> Xóa học phần
        </button>
      </div>
      {mode && (
        <form id={panelId} key={mode} aria-busy={pending} onSubmit={(event) => { event.preventDefault(); void submit(); }}
          onKeyDown={(event) => { if (event.key === 'Escape' && !pending) cancel(); }}
          className={`space-y-2.5 rounded-lg border p-3 text-xs ${mode === 'rename' ? 'border-slate-200 bg-slate-50' : 'border-rose-200 bg-rose-50'}`}>
          {mode === 'rename' ? (
            <div className="space-y-1">
              <label htmlFor={`${panelId}-name`} className="block font-medium text-slate-700">Tên mới của học phần</label>
              <input id={`${panelId}-name`} value={name} onChange={(event) => setName(event.target.value)}
                required maxLength={100} autoFocus disabled={disabled || pending}
                className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 lg:text-sm" />
            </div>
          ) : (
            <div role="group" aria-label="Xác nhận xóa học phần" className="space-y-1 leading-5 text-rose-900">
              <p>Xóa <strong className="wrap-anywhere">{courseName}</strong> khỏi danh sách học phần?</p>
              <p>Tệp PDF vẫn được lưu trong hệ thống.</p>
            </div>
          )}
          {error && <p role="alert" className="leading-5 text-rose-700">{error}</p>}
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button type="button" onClick={cancel} disabled={pending} autoFocus={mode === 'delete'}
              className={`${secondaryButton} border-slate-200 bg-white text-slate-700 hover:bg-slate-100`}>Hủy</button>
            <button type="submit" disabled={disabled || pending || (mode === 'rename' && !canRename)}
              className={`${actionButton} ${mode === 'rename' ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-rose-700 hover:bg-rose-800'}`}>
              {mode === 'rename' ? (pending ? 'Đang lưu…' : 'Lưu tên') : (pending ? 'Đang xóa…' : 'Xác nhận xóa')}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
