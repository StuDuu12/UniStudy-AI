import React from 'react';
import { ExternalLink, FileText } from 'lucide-react';
import type { DocumentInfo } from '../../types/api';
import { getDocumentPdfUrl } from '../../services/api';

interface DocumentListProps {
  documents: DocumentInfo[];
  loading?: boolean;
  error?: string;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  loading,
  error,
  onOpenPdfViewer,
}) => {
  if (loading) {
    return (
      <div role="status" className="space-y-2 py-1">
        <span className="sr-only">Đang tải học liệu…</span>
        <div className="h-10 rounded-lg bg-slate-100 motion-safe:animate-pulse" />
        <div className="h-10 rounded-lg bg-slate-100 motion-safe:animate-pulse" />
      </div>
    );
  }
  if (error) {
    return <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>;
  }
  if (documents.length === 0) {
    return <p className="rounded-lg bg-slate-50 p-3 text-sm leading-5 text-slate-600">Chưa có tài liệu khả dụng.</p>;
  }

  return (
    <ul className="max-h-64 space-y-1 overflow-y-auto pr-1">
      {documents.map((doc) => {
        const pdfUrl = getDocumentPdfUrl(doc.document_id);
        const rowClass = 'flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-slate-800 hover:text-indigo-800 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500';
        const fileDetails = (
          <>
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-indigo-50 text-indigo-700">
              <FileText aria-hidden="true" className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="line-clamp-2 text-sm leading-4.5 font-medium wrap-anywhere">{doc.document_name}</span>
              {doc.page_count > 0 && <span className="block text-xs leading-4 text-slate-600">{doc.page_count} trang</span>}
            </span>
          </>
        );
        return (
          <li key={doc.document_id} className="flex items-center rounded-lg hover:bg-slate-50">
            {onOpenPdfViewer ? (
              <>
                <button
                  type="button"
                  className={rowClass}
                  title={doc.document_name}
                  onClick={() => onOpenPdfViewer(doc.document_id, doc.document_name, 1, doc.page_count)}
                >
                  {fileDetails}
                </button>
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noreferrer"
                  title="Mở tài liệu PDF trong tab mới"
                  aria-label={`Mở ${doc.document_name} trong tab mới`}
                  className="mr-1 grid size-8 shrink-0 place-items-center rounded-md text-slate-500 hover:bg-indigo-50 hover:text-indigo-800 focus-visible:ring-2 focus-visible:ring-indigo-500"
                >
                  <ExternalLink aria-hidden="true" className="size-4" />
                </a>
              </>
            ) : (
              <a href={pdfUrl} target="_blank" rel="noreferrer" title={doc.document_name} className={rowClass}>
                {fileDetails}
                <ExternalLink aria-hidden="true" className="size-4 shrink-0 text-slate-500" />
              </a>
            )}
          </li>
        );
      })}
    </ul>
  );
};
