import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

interface AnswerMarkdownProps {
  text: string;
  sourceLayout?: boolean;
  disableLinksAndImages?: boolean;
}

export function AnswerMarkdown({ text, sourceLayout, disableLinksAndImages }: AnswerMarkdownProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      disallowedElements={disableLinksAndImages ? ['a', 'img'] : undefined}
      unwrapDisallowed={disableLinksAndImages}
      components={{
        h2: ({ children }) => (
          <h2 className="mt-4 mb-2 border-b border-slate-100 pb-1 text-base font-bold text-slate-900">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="mt-3 mb-1.5 text-sm font-bold text-indigo-950">{children}</h3>
        ),
        h4: ({ children }) => (
          <h4 className="mt-2.5 mb-1 text-xs font-bold tracking-wider text-slate-800">{children}</h4>
        ),
        p: ({ children }) => <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-slate-950">{children}</strong>,
        ul: ({ children }) => <ul className="my-1.5 list-disc space-y-1 ps-5">{children}</ul>,
        ol: ({ children, start }) => (
          <ol start={start} className="my-1.5 list-decimal space-y-1 ps-7">{children}</ol>
        ),
        li: ({ children, node }) => {
          const offset = node?.position?.start.offset;
          const line = offset === undefined ? '' : text.slice(offset).split('\n', 1)[0];
          const number = /^(\d{1,9}[.)])\s/.exec(line)?.[1];
          const letter = sourceLayout && /^- (?:[A-Za-z]|[IVXLCDMivxlcdm]{2,})[.)]\s/.test(line);
          const bullet = sourceLayout && (line.startsWith('+ ') ? '❖' : line.startsWith('* ') ? '□' : undefined);
          const label = number || bullet;
          return (
            <li
              value={number ? Number.parseInt(number, 10) : undefined}
              style={label ? { listStyleType: `"${label} "` } : undefined}
              className={letter ? 'list-none pl-5 -indent-5 [&>ul]:indent-0 [&>ol]:indent-0' : 'pl-0.5'}
            >
              {children}
            </li>
          );
        },
        blockquote: ({ children }) => (
          <blockquote className="my-2.5 rounded-r-lg border-l-2 border-indigo-400 bg-indigo-50/60 px-3.5 py-2.5 [&>ol:last-child]:mb-0 [&>ul:last-child]:mb-0">
            {children}
          </blockquote>
        ),
        code: ({ children }) => (
          <code className="rounded-md border border-slate-200/80 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-indigo-700">
            {children}
          </code>
        ),
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto rounded-xl border border-slate-200 shadow-2xs">
            <table className="min-w-full divide-y divide-slate-200 text-xs sm:text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-slate-50 font-semibold text-slate-900">{children}</thead>,
        th: ({ children }) => <th className="px-3 py-2 text-left text-xs font-semibold text-slate-700">{children}</th>,
        td: ({ children }) => <td className="border-t border-slate-100 px-3 py-2 text-slate-700">{children}</td>,
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
