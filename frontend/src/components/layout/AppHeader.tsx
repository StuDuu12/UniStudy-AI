import React from 'react';
import { Menu, BookOpen, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';

interface AppHeaderProps {
  courseName: string;
  documentCount: number;
  catalogStatus: 'loading' | 'online' | 'offline';
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  courseName,
  documentCount,
  catalogStatus,
  sidebarOpen,
  onToggleSidebar,
}) => {
  return (
    <header className="h-14 border-b border-slate-200/90 bg-white/95 backdrop-blur-xs px-4 flex items-center justify-between shrink-0 z-20 shadow-2xs">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label="Mở menu điều hướng"
          aria-controls="study-sidebar"
          aria-expanded={sidebarOpen}
          className="lg:hidden p-1.5 rounded-xl text-slate-600 hover:text-indigo-600 hover:bg-slate-100 transition-colors cursor-pointer"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200/80 text-indigo-600 flex items-center justify-center shrink-0 shadow-2xs">
            <BookOpen className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex items-center gap-2">
            <h1 className="text-sm sm:text-base font-bold text-slate-900 truncate tracking-tight">
              {courseName || 'UniStudy AI'}
            </h1>
            {documentCount > 0 && (
              <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200/80 shrink-0">
                {documentCount} học liệu PDF
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2.5 shrink-0">
        {/* AI & RAG Engine Pill */}
        <div className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] text-slate-600 font-medium">
          <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
          <span>Syllabus-Grounded RAG</span>
        </div>

        {/* Server Status */}
        <div
          className="flex items-center gap-1.5 text-xs text-slate-500"
          role="status"
        >
          {catalogStatus === 'loading' ? (
            <span className="inline-flex items-center gap-1 text-slate-500 text-xs">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="hidden sm:inline">Đang kết nối…</span>
            </span>
          ) : catalogStatus === 'online' ? (
            <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium text-xs bg-emerald-50/80 border border-emerald-200/70 px-2.5 py-1 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Hệ thống sẵn sàng</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-rose-700 font-medium text-xs bg-rose-50 border border-rose-200 px-2.5 py-1 rounded-full">
              <AlertCircle className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Mất kết nối</span>
            </span>
          )}
        </div>
      </div>
    </header>
  );
};
