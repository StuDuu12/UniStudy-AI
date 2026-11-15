import { useEffect, useMemo, useState } from 'react';
import type { PDFDocumentLoadingTask } from 'pdfjs-dist';
import { getDocumentPdfUrl } from '../../services/api';

type SearchStatus = 'idle' | 'loading' | 'error' | 'ready' | 'no_text';

function normalizeSearchText(text: string) {
  return text.normalize('NFC').replace(/\s+/g, ' ').trim().toLocaleLowerCase('vi');
}

export function usePdfTextSearch(documentId: string) {
  const [query, setQuery] = useState('');
  const [requested, setRequested] = useState(false);
  const [documentText, setDocumentText] = useState<string[] | null>();

  useEffect(() => {
    if (!requested) return;

    let cancelled = false;
    let task: PDFDocumentLoadingTask | undefined;

    function destroyTask() {
      void task?.destroy().catch(() => undefined);
      task = undefined;
    }

    async function readText() {
      try {
        const [pdfjs, { default: workerUrl }] = await Promise.all([
          import('pdfjs-dist'),
          import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
        ]);
        if (cancelled) return;

        pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
        task = pdfjs.getDocument({ url: getDocumentPdfUrl(documentId) });
        const pdf = await task.promise;
        const pages: string[] = [];

        for (let number = 1; number <= pdf.numPages && !cancelled; number++) {
          const page = await pdf.getPage(number);
          if (cancelled) return;
          const content = await page.getTextContent();
          pages.push(normalizeSearchText(content.items.map((item) => 'str' in item ? item.str : '').join(' ')));
        }

        if (!cancelled) setDocumentText(pages);
      } catch {
        if (!cancelled) setDocumentText(null);
      } finally {
        destroyTask();
      }
    }

    void readText();
    return () => {
      cancelled = true;
      destroyTask();
    };
  }, [documentId, requested]);

  function changeQuery(value: string) {
    setQuery(value);
    if (value.trim()) {
      setRequested(true);
    } else if (documentText === null) {
      setRequested(false);
      setDocumentText(undefined);
    }
  }

  const needle = normalizeSearchText(query);
  const matches = useMemo(() => {
    const pages = new Map<number, number>();
    if (!needle || !documentText) return pages;

    documentText.forEach((text, index) => {
      let count = 0;
      let position = text.indexOf(needle);
      while (position !== -1) {
        count++;
        position = text.indexOf(needle, position + needle.length);
      }
      if (count > 0) pages.set(index + 1, count);
    });
    return pages;
  }, [documentText, needle]);

  const status: SearchStatus = !needle ? 'idle'
    : documentText === undefined ? 'loading'
    : documentText === null ? 'error'
    : documentText.some(Boolean) ? 'ready' : 'no_text';

  return { query, changeQuery, matches, status };
}
