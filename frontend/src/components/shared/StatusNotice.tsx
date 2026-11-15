import React from 'react';
import { AlertCircle, AlertTriangle, HelpCircle, Info, RefreshCw } from 'lucide-react';
import type { ChatStatus } from '../../types/api';

interface StatusNoticeProps {
  status: ChatStatus;
  message?: string | null;
  onRetry?: () => void;
}

export const StatusNotice: React.FC<StatusNoticeProps> = ({
  status,
  message,
  onRetry,
}) => {
  if (status === 'success') return null;

  switch (status) {
    case 'insufficient_evidence':
      return (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-xl p-4 my-3 flex items-start gap-3 text-sm">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-amber-800">Không đủ căn cứ trong học liệu</p>
            <p className="mt-1 text-amber-700">
              {message || 'Chưa tìm thấy căn cứ đủ phù hợp trong tài liệu đã nạp của học phần này.'}
            </p>
          </div>
        </div>
      );

    case 'needs_clarification':
      return (
        <div className="bg-sky-50 border border-sky-200 text-sky-900 rounded-xl p-4 my-3 flex items-start gap-3 text-sm">
          <HelpCircle className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-sky-800">Cần làm rõ câu hỏi</p>
            <p className="mt-1 text-sky-700">
              {message || 'Bạn có thể nêu rõ khái niệm, chủ đề hoặc chương đang muốn hỏi không?'}
            </p>
          </div>
        </div>
      );

    case 'no_documents':
      return (
        <div className="bg-slate-50 border border-slate-200 text-slate-700 rounded-xl p-4 my-3 flex items-start gap-3 text-sm">
          <Info className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-slate-800">Chưa có tài liệu khả dụng</p>
            <p className="mt-1 text-slate-600">
              {message || 'Học phần này hiện chưa có tệp PDF nào được nạp vào hệ thống.'}
            </p>
          </div>
        </div>
      );

    case 'ai_unavailable':
    case 'error':
      return (
        <div className="bg-rose-50 border border-rose-200 text-rose-900 rounded-xl p-4 my-3 flex items-start gap-3 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-rose-800">
              {status === 'ai_unavailable' ? 'Chưa tạo được lời giải thích AI' : 'Không thể tra cứu học liệu'}
            </p>
            <p className="mt-1 text-rose-700">
              {message || 'Không thể kết nối đến hệ thống. Vui lòng kiểm tra và thử lại.'}
            </p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-2.5 inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-rose-300 text-rose-700 text-xs font-medium rounded-lg hover:bg-rose-50 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Thử lại
              </button>
            )}
          </div>
        </div>
      );

    case 'invalid_input':
      return (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-3 my-2 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{message || 'Vui lòng nhập câu hỏi hợp lệ.'}</span>
        </div>
      );

    default:
      return null;
  }
};
