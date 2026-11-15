import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  X,
  ExternalLink,
  Download,
  FileText,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Search,
  List,
  Layers,
  Loader2,
} from 'lucide-react';
import {
  getDocumentPdfUrl,
  getDocumentDownloadUrl,
  getDocumentPagePreviewUrl,
  fetchDocumentInfo,
} from '../../services/api';
import { usePdfTextSearch } from './usePdfTextSearch';

interface PdfViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  documentName: string;
  page: number;
  initialTotalPages?: number;
}

type ViewMode = 'scroll' | 'single';

interface PdfViewerProps extends Omit<PdfViewerModalProps, 'isOpen'> {
  zoomPercent: number;
  setZoomPercent: React.Dispatch<React.SetStateAction<number>>;
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

const SEARCH_STATUS = {
  idle: '',
  loading: 'Đang tìm…',
  error: 'Không thể đọc văn bản PDF.',
  no_text: 'PDF không có lớp văn bản để tìm kiếm.',
};

export const PdfViewerModal: React.FC<PdfViewerModalProps> = ({ isOpen, ...viewerProps }) => {
  const [zoomPercent, setZoomPercent] = useState(100);
  const [viewMode, setViewMode] = useState<ViewMode>('scroll');
  if (!isOpen || !viewerProps.documentId) return null;

  return (
    <PdfViewer
      key={`${viewerProps.documentId}:${viewerProps.page}`}
      {...viewerProps}
      zoomPercent={zoomPercent}
      setZoomPercent={setZoomPercent}
      viewMode={viewMode}
      setViewMode={setViewMode}
    />
  );
};

function PdfViewer({
  onClose,
  documentId,
  documentName,
  page,
  initialTotalPages,
  zoomPercent,
  setZoomPercent,
  viewMode,
  setViewMode,
}: PdfViewerProps) {
  const [fetchedPageCount, setFetchedPageCount] = useState<number>();
  const [currentPage, setCurrentPage] = useState(page || 1);
  const [pageInput, setPageInput] = useState(String(page || 1));
  const totalPages = fetchedPageCount ?? initialTotalPages ?? 0;
  const loadingInfo = totalPages === 0;

  const { query, changeQuery, matches, status: searchStatus } = usePdfTextSearch(documentId);
  const searchPages = useMemo(() => Array.from(matches.keys()), [matches]);
  const matchIndex = searchPages.indexOf(currentPage);
  const searchMessage = searchStatus !== 'ready' ? SEARCH_STATUS[searchStatus]
    : searchPages.length > 0 ? `${matchIndex < 0 ? '–' : matchIndex + 1}/${searchPages.length} trang khớp`
    : 'Không tìm thấy kết quả.';

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const searchInputRef = useRef<HTMLInputElement>(null);

  const scrollToPage = useCallback((pageNumber: number) => {
    if (scrollContainerRef.current) {
      // Anchor the requested page before preceding preview images change height.
      pageRefs.current.get(pageNumber)?.scrollIntoView({ behavior: 'instant', block: 'start' });
    }
  }, []);

  const showPage = useCallback((pageNumber: number) => {
    setCurrentPage(pageNumber);
    setPageInput(String(pageNumber));
    scrollToPage(pageNumber);
  }, [scrollToPage]);

  const handlePrevPage = useCallback(() => {
    if (currentPage > 1) showPage(currentPage - 1);
  }, [currentPage, showPage]);

  const handleNextPage = useCallback(() => {
    if (currentPage < totalPages) showPage(currentPage + 1);
  }, [currentPage, showPage, totalPages]);

  function navigateMatch(direction: 'next' | 'previous') {
    const target = direction === 'next'
      ? searchPages.find((number) => number > currentPage) ?? searchPages[0]
      : searchPages.findLast((number) => number < currentPage) ?? searchPages.at(-1);
    if (target !== undefined) showPage(target);
  }

  useEffect(() => {
    if (searchPages.length === 0) return;
    const frame = requestAnimationFrame(() => showPage(searchPages[0]));
    return () => cancelAnimationFrame(frame);
  }, [searchPages, showPage]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {
        event.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
        return;
      }
      if (event.key === 'Escape' && !event.isComposing) onClose();
      if (viewMode !== 'single' || event.target instanceof HTMLInputElement) return;

      if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
        event.preventDefault();
        handlePrevPage();
      } else if (event.key === 'ArrowRight' || event.key === 'PageDown') {
        event.preventDefault();
        handleNextPage();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, viewMode, handlePrevPage, handleNextPage]);

  useEffect(() => {
    const controller = new AbortController();
    const knownCount = initialTotalPages || 0;

    fetchDocumentInfo(documentId, controller.signal)
      .then((info) => {
        if (!controller.signal.aborted) setFetchedPageCount(info.page_count || Math.max(knownCount, page || 1));
      })
      .catch(() => {
        if (!controller.signal.aborted) setFetchedPageCount(Math.max(knownCount, page || 1));
      });

    return () => controller.abort();
  }, [documentId, page, initialTotalPages]);

  useEffect(() => {
    if (totalPages > 0 && viewMode === 'scroll') scrollToPage(currentPage);
  }, [viewMode, currentPage, totalPages, scrollToPage]);

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(pageInput, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= (totalPages || 1)) {
      showPage(parsed);
    } else {
      setPageInput(String(currentPage));
    }
  };

  const handleZoomIn = () => setZoomPercent((prev) => Math.min(prev + 20, 200));
  const handleZoomOut = () => setZoomPercent((prev) => Math.max(prev - 20, 50));
  const handleZoomReset = () => setZoomPercent(100);

  const pdfUrl = `${getDocumentPdfUrl(documentId)}#page=${currentPage}`;
  const downloadUrl = getDocumentDownloadUrl(documentId);

  // Array of page numbers
  const pagesList = Array.from({ length: totalPages || 1 }, (_, i) => i + 1);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-slate-900/80 backdrop-blur-xs animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-700/80 w-full max-w-6xl h-[95vh] flex flex-col overflow-hidden text-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div className="px-4 py-2.5 bg-slate-850 border-b border-slate-750 flex items-center justify-between shrink-0 gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
              <FileText className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-white truncate max-w-md sm:max-w-lg" title={documentName}>
                {documentName}
              </h3>
              <p className="text-[11px] text-slate-400 flex items-center gap-1.5 flex-wrap">
                {totalPages > 0 && (
                  <span className="font-semibold text-indigo-300">
                    Tổng cộng {totalPages} trang
                  </span>
                )}
                <span>• Đang hiển thị trực tiếp (không tự tải về)</span>
              </p>
            </div>
          </div>

          {/* Quick External Actions */}
          <div className="flex items-center gap-2 shrink-0">
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
              title="Mở tệp PDF gốc trong tab mới của trình duyệt"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Mở tab mới</span>
            </a>

            <a
              href={downloadUrl}
              download={documentName}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
              title="Tải tệp PDF này về máy"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Tải về</span>
            </a>

            <button
              type="button"
              onClick={onClose}
              aria-label="Đóng"
              className="w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center transition-colors ml-1 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Toolbar: Navigation, Zoom & Display Mode */}
        <div className="px-4 py-2 bg-slate-800/95 border-b border-slate-700/80 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0 select-none">
          {/* Page Navigator */}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={handlePrevPage}
              disabled={currentPage <= 1}
              className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer"
              title="Trang trước (Phím mũi tên trái)"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <form onSubmit={handlePageInputSubmit} className="flex items-center gap-1">
              <span className="text-slate-400">Trang</span>
              <input
                type="text"
                inputMode="numeric"
                aria-label="Số trang PDF"
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value)}
                onBlur={handlePageInputSubmit}
                className="w-12 text-center py-0.5 px-1 bg-slate-900 border border-slate-700 rounded-md text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
              />
              <span className="text-slate-400">/ {totalPages || '...'}</span>
            </form>

            <button
              type="button"
              onClick={handleNextPage}
              disabled={currentPage >= totalPages}
              className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-transparent cursor-pointer"
              title="Trang sau (Phím mũi tên phải)"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="flex min-w-0 basis-full flex-wrap items-center gap-1.5 sm:basis-auto">
            <div className="flex min-w-0 grow items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-0.5 focus-within:border-indigo-400">
              <Search aria-hidden="true" className="size-4 shrink-0 text-slate-400" />
              <input
                ref={searchInputRef}
                type="search"
                aria-label="Tìm trong PDF"
                placeholder="Tìm trong PDF"
                value={query}
                onChange={(event) => changeQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.nativeEvent.isComposing) return;
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    navigateMatch(event.shiftKey ? 'previous' : 'next');
                  } else if (event.key === 'Escape' && query) {
                    event.preventDefault();
                    event.stopPropagation();
                    changeQuery('');
                  }
                }}
                className="min-w-0 flex-1 bg-transparent py-1 text-base text-white outline-none placeholder:text-slate-400 sm:w-28 sm:text-xs lg:w-36 [&::-webkit-search-cancel-button]:hidden"
              />
              {query && (
                <button
                  type="button"
                  aria-label="Xóa tìm kiếm"
                  title="Xóa tìm kiếm"
                  onClick={() => {
                    changeQuery('');
                    searchInputRef.current?.focus();
                  }}
                  className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-md text-slate-300 hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-400"
                >
                  <X aria-hidden="true" className="size-3.5" />
                </button>
              )}
            </div>
            <button
              type="button"
              aria-label="Trang khớp trước"
              title="Trang khớp trước (Shift + Enter)"
              disabled={searchPages.length === 0}
              onClick={() => navigateMatch('previous')}
              className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-md text-slate-300 hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronUp aria-hidden="true" className="size-4" />
            </button>
            <button
              type="button"
              aria-label="Trang khớp sau"
              title="Trang khớp sau (Enter)"
              disabled={searchPages.length === 0}
              onClick={() => navigateMatch('next')}
              className="grid size-7 shrink-0 cursor-pointer place-items-center rounded-md text-slate-300 hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronDown aria-hidden="true" className="size-4" />
            </button>
            <span role="status" className="tabular-nums text-slate-300">{searchMessage}</span>
          </div>

          {/* View Mode Toggle: Scroll all pages vs Single page */}
          <div className="flex items-center bg-slate-900 rounded-lg p-0.5 border border-slate-700">
            <button
              type="button"
              onClick={() => setViewMode('scroll')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                viewMode === 'scroll'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Xem tất cả các trang liên tục (cuộn để đọc)"
            >
              <List className="w-3.5 h-3.5" />
              <span>Cuộn tất cả trang</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('single')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                viewMode === 'single'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Xem từng trang một"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Từng trang</span>
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={handleZoomOut}
              className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-700 cursor-pointer"
              title="Thu nhỏ"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-slate-400 font-mono w-10 text-center">{zoomPercent}%</span>
            <button
              type="button"
              onClick={handleZoomIn}
              className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-700 cursor-pointer"
              title="Phóng to"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handleZoomReset}
              className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-700 cursor-pointer ml-1"
              title="Vừa chiều rộng (100%)"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Viewer Content Area */}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto bg-slate-950 p-4 flex flex-col items-center"
        >
          {loadingInfo ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
              <p className="text-xs">Đang tải cấu trúc tài liệu PDF...</p>
            </div>
          ) : viewMode === 'scroll' ? (
            /* Continuous scroll view of all pages */
            <div
              className="flex flex-col items-center gap-8 py-2 w-full transition-all duration-150"
              style={{ maxWidth: `${Math.max(680, 850 * (zoomPercent / 100))}px` }}
            >
              {pagesList.map((pageNum) => (
                <div
                  key={pageNum}
                  id={`pdf-page-${pageNum}`}
                  ref={(el) => {
                    if (el) pageRefs.current.set(pageNum, el);
                    else pageRefs.current.delete(pageNum);
                  }}
                  className={`w-full flex flex-col items-center rounded-xl transition-all ${
                    pageNum !== currentPage ? 'shadow-lg shadow-black/40'
                      : matches.has(pageNum) ? 'ring-2 ring-amber-400 shadow-2xl shadow-amber-900/30'
                      : 'ring-2 ring-indigo-500/80 shadow-2xl shadow-indigo-900/30'
                  }`}
                >
                  {/* Page Indicator Badge */}
                  <div className="w-full flex items-center justify-between px-3 py-1 bg-slate-850/90 rounded-t-xl border border-b-0 border-slate-700/60 text-[11px] text-slate-400">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-300">Trang {pageNum} / {totalPages}</span>
                      {matches.has(pageNum) && (
                        <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-semibold text-amber-300">
                          {matches.get(pageNum)} kết quả
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => showPage(pageNum)}
                      className="text-indigo-400 hover:text-indigo-300 cursor-pointer"
                    >
                      {pageNum === currentPage ? '● Đang chọn' : 'Chọn trang này'}
                    </button>
                  </div>

                  {/* Rendered Page Image (Always reliable, never downloads) */}
                  <div className="w-full bg-white rounded-b-xl overflow-hidden border border-slate-700/60 flex items-center justify-center min-h-[500px]">
                    <img
                      src={getDocumentPagePreviewUrl(documentId, pageNum)}
                      alt={`Tài liệu ${documentName} - Trang ${pageNum}`}
                      loading="lazy"
                      className="w-full h-auto object-contain block select-text"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Single page view */
            <div
              className="flex flex-col items-center gap-3 py-2 w-full my-auto transition-all duration-150"
              style={{ maxWidth: `${Math.max(680, 850 * (zoomPercent / 100))}px` }}
            >
              <div className="w-full flex items-center justify-between px-3 py-1 bg-slate-850/90 rounded-t-xl border border-b-0 border-slate-700/60 text-xs text-slate-300">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-indigo-400">Trang {currentPage} / {totalPages}</span>
                  {matches.has(currentPage) && (
                    <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-semibold text-amber-300">
                      {matches.get(currentPage)} kết quả
                    </span>
                  )}
                </div>
                <span className="text-slate-400 text-[11px]">Dùng mũi tên ← / → để chuyển trang</span>
              </div>
              <div className="w-full bg-white rounded-b-xl overflow-hidden shadow-2xl border border-slate-700/60 flex items-center justify-center min-h-[600px]">
                <img
                  key={`single-${currentPage}`}
                  src={getDocumentPagePreviewUrl(documentId, currentPage)}
                  alt={`Tài liệu ${documentName} - Trang ${currentPage}`}
                  className="w-full h-auto object-contain block select-text"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
