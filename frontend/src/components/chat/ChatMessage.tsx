import React, { useEffect, useState } from 'react';
import { User, Sparkles, BookOpen, Copy, Check, ShieldCheck, ChevronsUpDown } from 'lucide-react';
import type { Message, Source } from '../../types/api';
import { fetchFormattedExcerpt } from '../../services/api';
import { restorePdfWordSpacing } from '../../services/pdfSpacing';
import { SourceCard } from '../sources/SourceCard';
import { StatusNotice } from '../shared/StatusNotice';
import { AnswerMarkdown } from '../shared/AnswerMarkdown';

interface ChatMessageProps {
  message: Message;
  onRetry?: () => void;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

const getModelBadgeLabel = (provider?: string, modelName?: string): string => {
  if (modelName) {
    const map: Record<string, string> = {
      'lookup': 'Tra cứu giáo trình',
      'qwen3.5:4b': 'Qwen 3.5 (4B)',
      'qwen3.5:2b': 'Qwen 3.5 (2B)',
      'qwen3.5:9b': 'Qwen 3.5 (9B)',
      'gemma4:e4b': 'Gemma 4 E4B IT',
      'qwen2.5:3b': 'Qwen 2.5 (3B)',
      'qwen2.5:7b': 'Qwen 2.5 (7B)',
      'llama3.2:3b': 'Llama 3.2 (3B)',
      'qwen2.5:1.5b': 'Qwen 2.5 (1.5B)',
      'gpt-6-astra': 'GPT-6 Astra',
      'gpt-6.1-sol': 'GPT-6.1 Sol',
      'gpt-6.1-terra': 'GPT-6.1 Terra',
      'gpt-6-luna': 'GPT-6 Luna',
      'gemini-3.8-flash': 'Gemini 3.8 Flash',
      'gemini-3.7-flash': 'Gemini 3.7 Flash',
      'gemini-3.6-flash': 'Gemini 3.6 Flash',
      'gemini-3.5-flash': 'Gemini 3.5 Flash',
      'gemini-3.5-flash-lite': 'Gemini 3.5 Flash-Lite',
      'gemini-3.1-pro-preview': 'Gemini 3.1 Pro Preview',
      'gemini-2.0-flash': 'Gemini 2.0 Flash',
      'gemini-2.0-flash-lite': 'Gemini 2.0 Flash-Lite',
      'gemini-2.0-pro-exp-02-05': 'Gemini 2.0 Pro',
      'gemini-1.5-flash': 'Gemini 1.5 Flash',
      'gemini-1.5-pro': 'Gemini 1.5 Pro',
      'o3-mini': 'OpenAI o3-mini',
      'o1-mini': 'OpenAI o1-mini',
      'gpt-4o': 'GPT-4o (Omni)',
      'gpt-4o-mini': 'GPT-4o-mini',
    };
    if (map[modelName]) return map[modelName];
    return modelName;
  }
  if (provider === 'chatgpt') return 'ChatGPT (OpenAI)';
  if (provider === 'gemini') return 'Gemini (Google)';
  if (provider === 'local') return 'Local (Tra cứu)';
  return 'Giải thích AI';
};

const LOOKUP_CITATION = /^Theo giáo trình \*\*(.+)\*\* \(Trang (\d+)\):$/m;

function legacyLookupSource(content: string, sources?: Source[]): Source | undefined {
  const [header, ...lines] = content.split(/\r?\n/);
  const citation = LOOKUP_CITATION.exec(header);
  if (!citation || !lines.some((line) => line.startsWith('>'))) return;
  if (lines.some((line) => line.trim() && !line.startsWith('>'))) return;
  return sources?.find((source) => source.document_name === citation[1]
    && source.page === Number(citation[2]) && source.document_sha256);
}

function formatLookupAnswer(text: string): string {
  return text.split(/\r?\n/).flatMap((rawLine) => {
    if (LOOKUP_CITATION.test(rawLine)) return rawLine;
    let line = restorePdfWordSpacing(rawLine);

    // Split inline numbered list items if joined on one line: e.g. "1. Item A 2. Item B"
    line = line.replace(/(?<=\S)[ \t]+(?=(?:\d{1,2}[.)]|[a-zA-Z][.)])[ \t]+[\p{L}\p{M}])/gu, '\n');

    return line.split(/\r?\n/).flatMap((subLine) => {
      if (!subLine.includes('•') && !/(?<=\S)[ \t]+[-+*][ \t]+[\p{L}\p{M}]/u.test(subLine)) {
        return subLine;
      }
      const leader = subLine.match(/^(?:[ \t]*>[ \t]?)*[ \t]*/)?.[0] ?? '';
      const prefix = leader.endsWith('>') ? `${leader} ` : leader;
      const content = subLine.slice(leader.length);

      if (content.includes('•')) {
        const parts = content.split(/[ \t]*•[ \t]*/);
        const intro = parts[0]?.trim();
        const items = parts.slice(1).map((item) => item.trim()).filter(Boolean);

        const lines: string[] = [];
        if (intro) {
          lines.push(intro);
        }
        for (const item of items) {
          lines.push(`- ${item}`);
        }
        return lines.map((part) => `${prefix}${part}`);
      }

      const dashParts = content.split(/(?<=\S)[ \t]+(?=[-+*][ \t]+[\p{L}\p{M}])/u);
      return dashParts.map((p) => `${prefix}${p.trim()}`);
    });
  }).join('\n');
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onRetry,
  onOpenPdfViewer,
}) => {
  const [copied, setCopied] = useState(false);
  const [expandAllSources, setExpandAllSources] = useState(false);
  const [recovered, setRecovered] = useState<{ messageId: string; markdown: string }>();
  const isUser = message.sender === 'user';
  const isLookup = !isUser && (message.mode === 'lookup'
    || (!message.mode && LOOKUP_CITATION.test(message.content)));
  const legacySource = isLookup && message.status === 'success'
    ? legacyLookupSource(message.content, message.sources)
    : undefined;

  useEffect(() => {
    if (!legacySource || legacySource.formatted_excerpt) return;
    const controller = new AbortController();
    void fetchFormattedExcerpt(legacySource, controller.signal).then((markdown) => {
      if (!controller.signal.aborted) setRecovered({ messageId: message.id, markdown });
    }).catch(() => {
      // Older history can still be read if its PDF is no longer available.
    });
    return () => controller.abort();
  }, [legacySource, message.id]);

  const recoveredExcerpt = legacySource
    ? legacySource.formatted_excerpt || (recovered?.messageId === message.id ? recovered.markdown : '')
    : '';
  const answer = recoveredExcerpt
    ? `${message.content.split(/\r?\n/, 1)[0]}\n\n${recoveredExcerpt}`
    : isLookup ? formatLookupAnswer(message.content) : message.content;

  const handleCopy = () => {
    if (!answer) return;
    navigator.clipboard.writeText(answer).then(() => {
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
  const isAi = message.mode === 'ai';

  return (
    <div className="flex justify-start my-4 animate-in fade-in duration-150">
      <div className="flex items-start gap-3 max-w-3xl w-full">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow-2xs flex items-center justify-center shrink-0 mt-1">
          <Sparkles className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0 bg-white border border-slate-200/90 rounded-2xl rounded-tl-xs p-4 sm:p-5 shadow-xs space-y-3.5 transition-shadow hover:shadow-sm">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-slate-900 tracking-tight">UniStudy AI</span>
              {isAi ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/70">
                  <Sparkles className="w-2.5 h-2.5 text-indigo-500" />
                  {getModelBadgeLabel(message.provider, message.model_name)}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200/70">
                  <BookOpen className="w-2.5 h-2.5 text-sky-500" />
                  {getModelBadgeLabel(message.provider, message.model_name)}
                </span>
              )}
              {hasSources && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/70">
                  <ShieldCheck className="w-2.5 h-2.5 text-emerald-600" />
                  Đối chiếu giáo trình ({message.sources!.length})
                </span>
              )}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">{message.timestamp}</span>
          </div>

          {/* Status notices for special states */}
          {message.status && message.status !== 'success' && (
            <StatusNotice
              status={message.status}
              message={
                message.message ||
                message.content ||
                (message.status === 'ai_unavailable'
                  ? 'Không thể kết nối đến máy chủ Local Model (Ollama tại http://127.0.0.1:11434). Hãy khởi động Ollama và bảo đảm mô hình đã chọn đã được tải về, hoặc chọn "Tra cứu giáo trình (Offline)" trên thanh công cụ.'
                  : undefined)
              }
              onRetry={onRetry}
            />
          )}

          {/* Answer text formatted with Markdown & LaTeX */}
          {answer && message.status === 'success' && (
            <div className="text-sm leading-relaxed wrap-anywhere text-slate-800 selection:bg-indigo-100 selection:text-indigo-900">
              <AnswerMarkdown text={answer} sourceLayout={isLookup} />
            </div>
          )}

          {/* Actions Bar */}
          {answer && message.status === 'success' && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-slate-500 hover:text-indigo-700 hover:bg-indigo-50/80 transition-colors cursor-pointer font-medium"
                title="Sao chép nội dung câu trả lời"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-600 font-semibold">Đã sao chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Sao chép</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Source cards section */}
          {hasSources && (
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                <div className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Nguồn trích dẫn đối chiếu ({message.sources!.length})</span>
                </div>
                {message.sources!.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setExpandAllSources(!expandAllSources)}
                    className="inline-flex items-center gap-1 text-[11px] text-indigo-600 hover:text-indigo-800 transition-colors font-medium cursor-pointer"
                  >
                    <ChevronsUpDown className="w-3 h-3" />
                    <span>{expandAllSources ? 'Thu gọn tất cả' : 'Mở rộng tất cả'}</span>
                  </button>
                )}
              </div>
              <div className="space-y-1.5">
                {message.sources!.map((source, idx) => (
                  <SourceCard
                    key={`${source.chunk_id || idx}-${expandAllSources}`}
                    source={recoveredExcerpt && source === legacySource
                      ? { ...source, formatted_excerpt: recoveredExcerpt }
                      : source}
                    index={idx + 1}
                    initiallyExpanded={expandAllSources}
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
