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
      return (
        <div className="bg-rose-50 border border-rose-200 text-rose-900 rounded-xl p-4 my-3 flex items-start gap-3 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-rose-900">Không thể kết nối đến máy chủ mô hình AI</p>
            <p className="mt-1 text-rose-800 leading-relaxed">
              {message ||
                'Không thể kết nối đến máy chủ mô hình AI (Ollama tại http://127.0.0.1:11434 hoặc nhà cung cấp API). Hãy khởi động Ollama và bảo đảm mô hình đã chọn đã được tải về, hoặc chọn "Tra cứu giáo trình (Offline)" trên thanh công cụ.'}
            </p>
            <div className="mt-2.5 text-xs text-rose-800 bg-rose-100/70 p-2.5 rounded-lg border border-rose-200 leading-relaxed">
              <span className="font-semibold">Cách khắc phục:</span>
              <ul className="list-disc ps-4 mt-1 space-y-1">
                <li>
                  Nếu dùng <strong>Local Model</strong>: Mở terminal chạy lệnh <code className="bg-white/90 px-1 py-0.5 rounded font-mono text-[11px] text-rose-950 border border-rose-200">ollama serve</code> và kiểm tra mô hình đã tải bằng <code className="bg-white/90 px-1 py-0.5 rounded font-mono text-[11px] text-rose-950 border border-rose-200">ollama list</code>.
                </li>
                <li>
                  Hoặc chuyển sang chế độ <strong>Tra cứu giáo trình (Offline)</strong> ở menu mô hình trên thanh công cụ để tra cứu trực tiếp từ tài liệu mà không cần chạy mô hình AI.
                </li>
              </ul>
            </div>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-rose-300 text-rose-700 text-xs font-semibold rounded-lg hover:bg-rose-100 transition-colors shadow-2xs cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Thử lại
              </button>
            )}
          </div>
        </div>
      );

    case 'error':
      return (
        <div className="bg-rose-50 border border-rose-200 text-rose-900 rounded-xl p-4 my-3 flex items-start gap-3 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-rose-800">Không thể tra cứu học liệu</p>
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
