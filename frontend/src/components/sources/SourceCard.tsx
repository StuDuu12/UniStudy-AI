import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Image as ImageIcon, ExternalLink, BookOpen } from 'lucide-react';
import type { Source } from '../../types/api';
import { getDocumentPagePreviewUrl, getDocumentPdfUrl } from '../../services/api';

interface SourceCardProps {
  source: Source;
  index: number;
  initiallyExpanded?: boolean;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

export const SourceCard: React.FC<SourceCardProps> = ({
  source,
  index,
  initiallyExpanded = false,
  onOpenPdfViewer,
}) => {
  const [isOpen, setIsOpen] = useState(initiallyExpanded);
  const [showImagePreview, setShowImagePreview] = useState(false);
  const [previewError, setPreviewError] = useState(false);

  const pdfUrl = getDocumentPdfUrl(source.document_id, source.page);

  return (
    <div className="border border-slate-200 rounded-xl bg-white overflow-hidden shadow-xs hover:border-indigo-300 transition-colors">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-3 text-left cursor-pointer bg-slate-50/70 hover:bg-slate-100/70 transition-colors text-xs select-none"
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-5 h-5 rounded-md bg-indigo-100 text-indigo-700 font-semibold flex items-center justify-center text-[10px] shrink-0">
            {index}
          </div>
          <FileText className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
          <span className="font-semibold text-slate-800 truncate" title={source.document_name}>
            {source.document_name}
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200/60 shrink-0">
            Trang PDF {source.page}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {source.score !== null && (
            <span className="hidden sm:inline text-[10px] text-slate-400 font-mono" title="Điểm tương đồng Cosine">
              độ khớp: {source.score}
            </span>
          )}
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="p-3.5 border-t border-slate-100 space-y-3">
          {/* Excerpt */}
          <div className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100 font-sans italic">
            "{source.excerpt}"
          </div>

          {/* Action buttons: View real PDF */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-100/80">
            <div className="flex items-center gap-2">
              {onOpenPdfViewer && (
                <button
                  type="button"
                  onClick={() => onOpenPdfViewer(source.document_id, source.document_name, source.page)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer"
                  title="Mở tài liệu PDF gốc tại đúng trang này"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Xem toàn bộ PDF (Trang {source.page})</span>
                </button>
              )}

              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
                title="Mở tệp PDF trong tab mới với trình đọc PDF của trình duyệt"
              >
                <span>Mở tab mới</span>
                <ExternalLink className="w-3 h-3 text-slate-500" />
              </a>
            </div>

            <button
              type="button"
              aria-expanded={showImagePreview}
              onClick={() => {
                setPreviewError(false);
                setShowImagePreview(!showImagePreview);
              }}
              className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 transition-colors"
            >
              <ImageIcon className="w-3 h-3" />
              <span>{showImagePreview ? 'Thu gọn ảnh' : 'Xem ảnh chụp trang'}</span>
            </button>
          </div>

          {showImagePreview && (
            previewError ? (
              <p role="status" className="text-xs text-slate-600">Không thể hiển thị ảnh trang PDF này.</p>
            ) : (
              <div className="mt-2 border border-slate-200 rounded-lg overflow-hidden bg-slate-100 p-1">
                <img
                  src={getDocumentPagePreviewUrl(source.document_id, source.page, source.document_sha256)}
                  alt={`Trang ${source.page} của ${source.document_name}`}
                  className="w-full h-auto rounded shadow-sm max-h-96 object-contain bg-white"
                  loading="lazy"
                  onError={() => setPreviewError(true)}
                />
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
};
