import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { User, Sparkles, BookOpen, Copy, Check, ShieldCheck } from 'lucide-react';
import type { Message } from '../../types/api';
import { SourceCard } from '../sources/SourceCard';
import { StatusNotice } from '../shared/StatusNotice';

interface ChatMessageProps {
  message: Message;
  onRetry?: () => void;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onRetry,
  onOpenPdfViewer,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.sender === 'user';

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (isUser) {
    return (
      <div className="flex justify-end my-4 animate-in fade-in duration-150">
        <div className="flex items-start gap-2.5 max-w-xl">
          <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-xs py-2.5 px-4 shadow-sm text-sm leading-relaxed font-normal selection:bg-indigo-400 selection:text-white">
            {message.content}
          </div>
          <div className="w-8 h-8 rounded-xl bg-indigo-100 border border-indigo-200 text-indigo-700 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
            <User className="w-4 h-4" />
          </div>
        </div>
      </div>
    );
  }

  // Assistant message
  const hasSources = message.sources && message.sources.length > 0;

  return (
    <div className="flex justify-start my-4 animate-in fade-in duration-150">
      <div className="flex items-start gap-3 max-w-3xl w-full">
        <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200/80 text-indigo-600 shadow-2xs flex items-center justify-center shrink-0 mt-1">
          <Sparkles className="w-4 h-4 text-indigo-600" />
        </div>

        <div className="flex-1 min-w-0 bg-white border border-slate-200/90 rounded-2xl rounded-tl-xs p-4 shadow-xs space-y-3 transition-shadow hover:shadow-sm">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-900 tracking-tight">UniStudy AI</span>
              {hasSources && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/70">
                  <ShieldCheck className="w-3 h-3" />
                  Đối chiếu giáo trình
                </span>
              )}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">{message.timestamp}</span>
          </div>

          {/* Status notices for special states */}
          {message.status && message.status !== 'success' && (
            <StatusNotice
              status={message.status}
              message={message.message || message.content}
              onRetry={onRetry}
            />
          )}

          {/* Answer text formatted with Markdown & LaTeX according to DESIGN.md */}
          {message.content && message.status === 'success' && (
            <div className="text-sm text-slate-800 leading-relaxed font-sans selection:bg-indigo-100 selection:text-indigo-900">
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  p: ({ children }) => <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>,
                  strong: ({ children }) => <strong className="font-semibold text-slate-950">{children}</strong>,
                  ul: ({ children }) => <ul className="my-2 ml-4 list-disc space-y-1 text-slate-800">{children}</ul>,
                  ol: ({ children }) => <ol className="my-2 ml-4 list-decimal space-y-1 text-slate-800">{children}</ol>,
                  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                  blockquote: ({ children }) => (
                    <blockquote className="my-2.5 border-l-3 border-indigo-500 bg-indigo-50/60 rounded-r-lg px-3.5 py-2 text-xs text-slate-700 italic">
                      {children}
                    </blockquote>
                  ),
                  code: ({ children }) => (
                    <code className="px-1.5 py-0.5 rounded bg-slate-100 text-indigo-700 font-mono text-xs border border-slate-200">
                      {children}
                    </code>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Actions Bar */}
          {message.content && message.status === 'success' && (
            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Sao chép nội dung câu trả lời"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span className="text-emerald-600 font-medium">Đã sao chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Sao chép</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Source cards */}
          {hasSources && (
            <div className="pt-2 border-t border-slate-100 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                <div className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Nguồn trích dẫn đối chiếu ({message.sources!.length})</span>
                </div>
                <span className="text-[11px] text-slate-400 font-normal">Nhấp để mở xem trực tiếp</span>
              </div>
              <div className="space-y-2">
                {message.sources!.map((source, idx) => (
                  <SourceCard
                    key={source.chunk_id || idx}
                    source={source}
                    index={idx + 1}
                    initiallyExpanded={idx === 0}
                    onOpenPdfViewer={onOpenPdfViewer}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
