import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Image as ImageIcon, ExternalLink, BookOpen } from 'lucide-react';
import type { Source } from '../../types/api';
import { getDocumentPagePreviewUrl, getDocumentPdfUrl } from '../../services/api';
import { restorePdfWordSpacing, formatSourceExcerpt } from '../../services/pdfSpacing';
import { AnswerMarkdown } from '../shared/AnswerMarkdown';

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
    <div className="border border-slate-200/90 rounded-xl bg-white overflow-hidden shadow-2xs hover:border-indigo-300 transition-colors">
      {/* Header bar */}
      <div
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsOpen(!isOpen);
          }
        }}
        className="flex w-full items-center justify-between p-2.5 sm:p-3 text-left cursor-pointer bg-slate-50/70 hover:bg-slate-100/70 transition-colors text-xs select-none gap-2"
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-5 h-5 rounded-md bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px] shrink-0">
            {index}
          </div>
          <FileText className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
          <span className="font-semibold text-slate-800 truncate text-xs" title={source.document_name}>
            {source.document_name}
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/70 shrink-0">
            Trang PDF {source.page}
          </span>
          {source.score !== null && (
            <span className="hidden md:inline text-[10px] text-slate-400 font-mono shrink-0" title="Điểm tương đồng Cosine">
              độ khớp: {source.score}
            </span>
          )}
        </div>

        {/* Action icons & expand toggle */}
        <div className="flex items-center gap-1.5 shrink-0">
          {onOpenPdfViewer && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenPdfViewer(source.document_id, source.document_name, source.page);
              }}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 active:bg-indigo-200 text-indigo-700 text-[11px] font-semibold border border-indigo-200/80 transition-colors shadow-2xs cursor-pointer"
              title={`Mở xem PDF tại đúng Trang ${source.page}`}
            >
              <BookOpen className="w-3 h-3 text-indigo-600" />
              <span className="hidden sm:inline">Xem PDF (Trang {source.page})</span>
              <span className="sm:hidden">Trang {source.page}</span>
            </button>
          )}

          <a
            href={pdfUrl}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/70 transition-colors cursor-pointer"
            title="Mở tệp PDF trong tab mới"
            aria-label="Mở PDF trong tab mới"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>

          <button
            type="button"
            aria-label={isOpen ? 'Thu gọn đoạn trích' : 'Mở rộng đoạn trích'}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 transition-colors"
          >
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Details: Clean Excerpt and Image Preview */}
      {isOpen && (
        <div className="p-3.5 border-t border-slate-100 space-y-2.5 bg-white">
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
            <span className="font-semibold text-slate-700">Đoạn trích đối chiếu từ giáo trình:</span>
            <button
              type="button"
              aria-expanded={showImagePreview}
              onClick={() => {
                setPreviewError(false);
                setShowImagePreview(!showImagePreview);
              }}
              className="inline-flex items-center gap-1 text-[11px] text-indigo-600 hover:text-indigo-800 transition-colors font-medium cursor-pointer"
            >
              <ImageIcon className="w-3.5 h-3.5" />
              <span>{showImagePreview ? 'Ẩn ảnh chụp trang' : 'Xem ảnh chụp trang PDF'}</span>
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto rounded-xl border border-slate-200/70 bg-slate-50/80 p-3 text-sm leading-relaxed wrap-anywhere text-slate-700 selection:bg-indigo-100">
            {source.formatted_excerpt ? (
              <AnswerMarkdown text={restorePdfWordSpacing(source.formatted_excerpt)} sourceLayout />
            ) : (
              <div className="whitespace-pre-line leading-relaxed font-normal text-slate-700">
                {formatSourceExcerpt(source.excerpt)}
              </div>
            )}
          </div>

          {showImagePreview && (
            previewError ? (
              <p role="status" className="text-xs text-slate-500 italic py-1">Không thể hiển thị ảnh trang PDF này.</p>
            ) : (
              <div className="mt-2 border border-slate-200 rounded-xl overflow-hidden bg-slate-100 p-1.5 shadow-2xs">
                <img
                  src={getDocumentPagePreviewUrl(source.document_id, source.page, source.document_sha256)}
                  alt={`Trang ${source.page} của ${source.document_name}`}
                  className="w-full h-auto rounded-lg shadow-xs max-h-96 object-contain bg-white"
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
