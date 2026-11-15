import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, Sparkles } from 'lucide-react';

const MAX_QUESTION_LENGTH = 1000;

interface ChatComposerProps {
  onSend: (question: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSend,
  disabled,
  placeholder = 'Nhập câu hỏi về bài giảng, khái niệm trong học phần...',
}) => {
  const [question, setQuestion] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSubmit = question.trim().length > 0 && !disabled;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [question]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!canSubmit) return;

    onSend(question.trim());
    setQuestion('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Check for IME composition (Vietnamese Telex/VNI typing)
    if (e.nativeEvent.isComposing) return;

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-slate-200/80 bg-white/95 backdrop-blur-xs p-3 sm:p-4 shrink-0">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-1.5">
        <div className="relative flex items-end bg-slate-50 border border-slate-200 rounded-2xl shadow-2xs focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:bg-white transition-all p-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={question}
            maxLength={MAX_QUESTION_LENGTH}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            aria-label="Câu hỏi"
            className="w-full bg-transparent resize-none border-0 focus:outline-none focus:ring-0 text-sm text-slate-900 placeholder-slate-400 py-1.5 px-2.5 max-h-40 min-h-[40px] leading-relaxed selection:bg-indigo-100"
          />

          <div className="flex items-center gap-2 pl-2 pb-1 shrink-0">
            <span className="hidden sm:inline-flex items-center text-[10px] text-slate-400 font-mono select-none pr-1">
              <CornerDownLeft className="w-2.5 h-2.5 mr-0.5 opacity-60" /> Enter
            </span>
            <button
              type="submit"
              disabled={!canSubmit}
              aria-label="Gửi câu hỏi"
              className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white disabled:text-slate-400 flex items-center justify-center transition-all duration-150 shadow-xs disabled:shadow-none cursor-pointer disabled:cursor-not-allowed hover:scale-105 active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Footer info & helper */}
        <div className="flex items-center justify-between px-2 text-[11px] text-slate-400">
          <span className="inline-flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-500/70" />
            <span>Đối chiếu trực tiếp với giáo trình PDF đã nạp</span>
          </span>
          {question.length > 700 && (
            <span className="font-mono">
              {question.length} / {MAX_QUESTION_LENGTH}
            </span>
          )}
        </div>
      </form>
    </div>
  );
};
