import React from 'react';
import { Search } from 'lucide-react';

export const LoadingSkeleton: React.FC = () => {
  return (
    <div role="status" className="flex gap-4 p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm animate-pulse">
      <div className="w-9 h-9 rounded-xl bg-indigo-100 flex items-center justify-center shrink-0">
        <Search className="w-5 h-5 text-indigo-500" />
      </div>

      <div className="flex-1 space-y-3 pt-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-indigo-700">UniStudy AI</span>
          <span className="text-[11px] text-slate-400">
            Đang tra cứu học liệu liên quan…
          </span>
        </div>

        <div className="space-y-2">
          <div className="h-4 bg-slate-100 rounded w-5/6" />
          <div className="h-4 bg-slate-100 rounded w-4/6" />
          <div className="h-4 bg-slate-100 rounded w-3/6" />
        </div>

        <div className="pt-2 flex gap-2">
          <div className="h-8 bg-slate-100 rounded-lg w-40" />
          <div className="h-8 bg-slate-100 rounded-lg w-32" />
        </div>
      </div>
    </div>
  );
};
