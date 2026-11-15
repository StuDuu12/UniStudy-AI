import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
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

if (typeof window !== 'undefined' && 'GlobalWorkerOptions' in pdfjsLib) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
  ).toString();
}
import {
  getDocumentPdfUrl,
  getDocumentDownloadUrl,
  getDocumentPagePreviewUrl,
  fetchDocumentInfo,
} from '../../services/api';

interface PdfViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  documentName: string;
  page: number;
  initialTotalPages?: number;
}

export const PdfViewerModal: React.FC<PdfViewerModalProps> = ({
  isOpen,
  onClose,
  documentId,
  documentName,
  page,
  initialTotalPages,
}) => {
  const [totalPages, setTotalPages] = useState<number>(initialTotalPages || 0);
  const [currentPage, setCurrentPage] = useState<number>(page || 1);
  const [loadingInfo, setLoadingInfo] = useState<boolean>(!initialTotalPages);
  const [zoomPercent, setZoomPercent] = useState<number>(100);
  const [viewMode, setViewMode] = useState<'scroll' | 'single'>('scroll');
  const [pageInput, setPageInput] = useState<string>(String(page || 1));

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<{ page: number }[]>([]);
  const [currentMatchIndex, setCurrentMatchIndex] = useState<number>(-1);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const searchInputRef = useRef<HTMLInputElement>(null);
  const textCacheRef = useRef<Map<string, Map<number, string>>>(new Map());

  const scrollToPage = (pageNum: number) => {
    const targetEl = pageRefs.current.get(pageNum);
    if (targetEl && scrollContainerRef.current) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setCurrentPage(pageNum);
      setPageInput(String(pageNum));
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      const next = currentPage - 1;
      setCurrentPage(next);
      setPageInput(String(next));
      if (viewMode === 'scroll') scrollToPage(next);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      const next = currentPage + 1;
      setCurrentPage(next);
      setPageInput(String(next));
      if (viewMode === 'scroll') scrollToPage(next);
    }
  };

  const jumpToMatchPage = (pageNum: number) => {
    setCurrentPage(pageNum);
    setPageInput(String(pageNum));
    if (viewMode === 'scroll') {
      scrollToPage(pageNum);
    }
  };

  const handleNextMatch = () => {
    if (searchResults.length === 0) return;
    const nextIdx = (currentMatchIndex + 1) % searchResults.length;
    setCurrentMatchIndex(nextIdx);
    jumpToMatchPage(searchResults[nextIdx].page);
  };

  const handlePrevMatch = () => {
    if (searchResults.length === 0) return;
    const prevIdx = (currentMatchIndex - 1 + searchResults.length) % searchResults.length;
    setCurrentMatchIndex(prevIdx);
    jumpToMatchPage(searchResults[prevIdx].page);
  };

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(pageInput, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= (totalPages || 1)) {
      setCurrentPage(parsed);
      if (viewMode === 'scroll') {
        scrollToPage(parsed);
      }
    } else {
      setPageInput(String(currentPage));
    }
  };

  const handleZoomIn = () => setZoomPercent((prev) => Math.min(prev + 20, 200));
  const handleZoomOut = () => setZoomPercent((prev) => Math.max(prev - 20, 50));
  const handleZoomReset = () => setZoomPercent(100);

  // Close on Escape key or focus search on Ctrl+F
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
      if (viewMode === 'single') {
        if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
          handlePrevPage();
        } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
          handleNextPage();
        }
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, viewMode, currentPage, totalPages]);

  // Fetch document details when opened
  useEffect(() => {
    if (!isOpen || !documentId) return;

    let isMounted = true;
    setCurrentPage(page || 1);
    setPageInput(String(page || 1));

    if (initialTotalPages && initialTotalPages > 0) {
      setTotalPages(initialTotalPages);
      setLoadingInfo(false);
      setTimeout(() => scrollToPage(page || 1), 80);
    } else {
      setLoadingInfo(true);
    }

    fetchDocumentInfo(documentId)
      .then((info) => {
        if (!isMounted) return;
        const count = info.page_count || initialTotalPages || 1;
        setTotalPages(count);
        setLoadingInfo(false);

        // Scroll to requested page after layout
        setTimeout(() => {
          scrollToPage(page || 1);
        }, 120);
      })
      .catch((err) => {
        console.warn('Could not fetch document details, using known count:', err);
        if (!isMounted) return;
        setTotalPages((prev) => prev > 0 ? prev : (initialTotalPages || page || 1));
        setLoadingInfo(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, documentId, page, initialTotalPages]);

  // Reset search when modal opens/closes or doc changes
  useEffect(() => {
    if (!isOpen) {
      setSearchQuery('');
      setSearchResults([]);
      setCurrentMatchIndex(-1);
      setIsSearching(false);
    }
  }, [isOpen, documentId]);

  // Execute text search using pdfjsLib
  useEffect(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query || !isOpen || !documentId) {
      setSearchResults([]);
      setCurrentMatchIndex(-1);
      setIsSearching(false);
      return;
    }

    let isMounted = true;
    setIsSearching(true);

    const timer = setTimeout(async () => {
      try {
        const docUrl = getDocumentDownloadUrl(documentId);
        const loadingTask = pdfjsLib.getDocument({ url: docUrl });
        const pdf = await loadingTask.promise;
        if (!isMounted) return;

        let docMap = textCacheRef.current.get(documentId);
        if (!docMap) {
          docMap = new Map<number, string>();
          textCacheRef.current.set(documentId, docMap);
        }

        const results: { page: number }[] = [];
        const count = pdf.numPages;

        for (let p = 1; p <= count; p++) {
          if (!isMounted) return;
          let pageText = docMap.get(p);
          if (pageText === undefined) {
            const pdfPage = await pdf.getPage(p);
            const content = await pdfPage.getTextContent();
            pageText = content.items
              .map((item) => ('str' in item ? (item as { str: string }).str : ''))
              .join(' ');
            docMap.set(p, pageText);
          }

          const lowerText = pageText.toLowerCase();
          let pos = 0;
          while ((pos = lowerText.indexOf(query, pos)) !== -1) {
            results.push({ page: p });
            pos += query.length;
          }
        }

        if (isMounted) {
          setSearchResults(results);
          if (results.length > 0) {
            setCurrentMatchIndex(0);
            const firstPage = results[0].page;
            setCurrentPage(firstPage);
            setPageInput(String(firstPage));
            if (viewMode === 'scroll') {
              setTimeout(() => scrollToPage(firstPage), 50);
            }
          } else {
            setCurrentMatchIndex(-1);
          }
        }
      } catch (err) {
        console.warn('PDF search failed:', err);
      } finally {
        if (isMounted) {
          setIsSearching(false);
        }
      }
    }, 250);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [searchQuery, isOpen, documentId, viewMode]);

  if (!isOpen || !documentId) return null;

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

          {/* Text Search Bar */}
          <div className="flex items-center gap-1.5 bg-slate-900 rounded-lg px-2.5 py-1 border border-slate-700 text-xs">
            <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Tìm kiếm trong tài liệu..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (e.shiftKey) handlePrevMatch();
                  else handleNextMatch();
                } else if (e.key === 'Escape' && searchQuery) {
                  e.stopPropagation();
                  setSearchQuery('');
                  setSearchResults([]);
                  setCurrentMatchIndex(-1);
                }
              }}
              className="w-28 sm:w-36 md:w-44 bg-transparent text-white placeholder-slate-500 text-xs focus:outline-none"
            />
            {isSearching ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 shrink-0" />
            ) : searchQuery.trim() ? (
              <span className="text-[11px] text-slate-400 font-mono shrink-0 px-1">
                {searchResults.length > 0
                  ? `${currentMatchIndex + 1}/${searchResults.length}`
                  : '0/0'}
              </span>
            ) : null}
            <button
              type="button"
              onClick={handlePrevMatch}
              disabled={searchResults.length === 0}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer"
              title="Kết quả trước (Shift + Enter)"
              aria-label="Kết quả trước"
            >
              <ChevronUp className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleNextMatch}
              disabled={searchResults.length === 0}
              className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer"
              title="Kết quả sau (Enter)"
              aria-label="Kết quả sau"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                  setCurrentMatchIndex(-1);
                }}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700 cursor-pointer"
                title="Xóa tìm kiếm"
                aria-label="Xóa tìm kiếm"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* View Mode Toggle: Scroll all pages vs Single page */}
          <div className="flex items-center bg-slate-900 rounded-lg p-0.5 border border-slate-700">
            <button
              type="button"
              onClick={() => {
                setViewMode('scroll');
                setTimeout(() => scrollToPage(currentPage), 50);
              }}
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
              {pagesList.map((pageNum) => {
                const pageMatchCount = searchResults.filter((r) => r.page === pageNum).length;
                const isCurrentMatch = searchResults[currentMatchIndex]?.page === pageNum;
                return (
                  <div
                    key={pageNum}
                    id={`pdf-page-${pageNum}`}
                    ref={(el) => {
                      if (el) pageRefs.current.set(pageNum, el);
                      else pageRefs.current.delete(pageNum);
                    }}
                    className={`w-full flex flex-col items-center rounded-xl transition-all ${
                      isCurrentMatch
                        ? 'ring-2 ring-amber-400 shadow-2xl shadow-amber-900/30'
                        : pageNum === currentPage
                        ? 'ring-2 ring-indigo-500/80 shadow-2xl shadow-indigo-900/30'
                        : 'shadow-lg shadow-black/40'
                    }`}
                  >
                    {/* Page Indicator Badge */}
                    <div className="w-full flex items-center justify-between px-3 py-1 bg-slate-850/90 rounded-t-xl border border-b-0 border-slate-700/60 text-[11px] text-slate-400">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-300">Trang {pageNum} / {totalPages}</span>
                        {pageMatchCount > 0 && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${isCurrentMatch ? 'bg-amber-400 text-slate-900' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'}`}>
                            {pageMatchCount} khớp
                          </span>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setCurrentPage(pageNum);
                          setPageInput(String(pageNum));
                        }}
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
                );
              })}
            </div>
          ) : (
            /* Single page view */
            (() => {
              const singlePageMatchCount = searchResults.filter((r) => r.page === currentPage).length;
              return (
                <div
                  className="flex flex-col items-center gap-3 py-2 w-full my-auto transition-all duration-150"
                  style={{ maxWidth: `${Math.max(680, 850 * (zoomPercent / 100))}px` }}
                >
                  <div className="w-full flex items-center justify-between px-3 py-1 bg-slate-850/90 rounded-t-xl border border-b-0 border-slate-700/60 text-xs text-slate-300">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-indigo-400">Trang {currentPage} / {totalPages}</span>
                      {singlePageMatchCount > 0 && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-400 text-slate-900">
                          {singlePageMatchCount} khớp
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
              );
            })()
          )}
        </div>
      </div>
    </div>
  );
};
