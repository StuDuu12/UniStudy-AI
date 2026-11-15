import { useId, useState } from 'react';
import type { FormEvent } from 'react';
import { ChevronDown, FileUp, Plus } from 'lucide-react';

interface CourseUploadFormProps {
  create?: boolean;
  disabled?: boolean;
  onUpload: (name: string, files: File[]) => Promise<void>;
}

export function CourseUploadForm({ create = false, disabled, onUpload }: CourseUploadFormProps) {
  const id = useId();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || disabled) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const name = String(data.get('course_name') ?? '').trim();
    const files = data.getAll('files').filter((file): file is File => file instanceof File && file.size > 0);
    setError('');
    setSuccess('');
    if (create && !name) {
      setError('Hãy nhập tên học phần.');
      return;
    }
    if (!files.length) {
      setError('Hãy chọn ít nhất một tệp PDF.');
      return;
    }

    setBusy(true);
    try {
      await onUpload(name, files);
      form.reset();
      setSuccess(create ? 'Đã thêm học phần.' : 'Đã thêm PDF vào học phần.');
    } catch (error) {
      setError(error instanceof Error && !(error instanceof TypeError)
        ? error.message
        : 'Không thể kết nối máy chủ để tải PDF.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="group rounded-lg border border-transparent open:border-slate-200 open:bg-slate-50">
      <summary className="flex min-h-10 cursor-pointer list-none items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-indigo-800 hover:bg-indigo-50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500 [&::-webkit-details-marker]:hidden">
        {create ? <Plus aria-hidden="true" className="size-4 shrink-0" /> : <FileUp aria-hidden="true" className="size-4 shrink-0" />}
        <span>{create ? 'Thêm học phần' : 'Thêm PDF vào học phần'}</span>
        <ChevronDown aria-hidden="true" className="ml-auto size-4 shrink-0 text-slate-500 transition-transform group-open:rotate-180 motion-reduce:transition-none" />
      </summary>
      <form onSubmit={handleSubmit} aria-busy={busy} className="space-y-3 px-3 pt-1 pb-3 text-xs">
        {create && (
          <div className="space-y-1">
            <label htmlFor={`${id}-name`} className="block font-medium text-slate-700">Tên học phần</label>
            <input
              id={`${id}-name`} name="course_name" required maxLength={100} disabled={busy || disabled}
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-base text-slate-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 lg:text-sm"
            />
          </div>
        )}
        <div className="space-y-1">
          <label htmlFor={`${id}-files`} className="block font-medium text-slate-700">
            {create ? 'Tệp PDF của học phần' : 'Tệp PDF cần thêm'}
          </label>
          <input
            id={`${id}-files`} name="files" type="file" accept="application/pdf,.pdf" multiple required disabled={busy || disabled}
            aria-describedby={`${id}-limit`}
            className="block w-full rounded-lg border border-dashed border-slate-300 bg-white p-1.5 text-slate-600 focus-visible:ring-2 focus-visible:ring-indigo-500 file:mr-2 file:cursor-pointer file:rounded-md file:border-0 file:bg-indigo-50 file:px-2 file:py-1.5 file:font-medium file:text-indigo-800"
          />
          <p id={`${id}-limit`} className="leading-4 text-slate-600">Tối đa 5 PDF mỗi lượt, 20 MB mỗi tệp.</p>
        </div>
        <button
          type="submit" disabled={busy || disabled}
          className="inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 font-semibold text-white hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <FileUp className="h-3.5 w-3.5" aria-hidden="true" />
          {busy ? 'Đang tải PDF…' : create ? 'Tạo học phần' : 'Tải PDF lên'}
        </button>
        {error && <p role="alert" className="text-rose-700">{error}</p>}
        {success && <p role="status" className="text-emerald-700">{success}</p>}
      </form>
    </details>
  );
}
