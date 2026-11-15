import React, { useEffect, useRef } from 'react';
import type { Message } from '../../types/api';
import { ChatMessage } from './ChatMessage';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  onRetry: (question: string) => void;
  onLookup: (question: string) => void;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  loading,
  onRetry,
  onLookup,
  onOpenPdfViewer,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.map((message, index) => {
        const retryQuestion = !loading && index === messages.length - 1 ? message.retryQuestion : undefined;
        return (
          <ChatMessage
            key={message.id}
            message={message}
            onRetry={retryQuestion ? () => onRetry(retryQuestion) : undefined}
            onLookup={retryQuestion && message.status === 'ai_unavailable' && message.sources?.length
              ? () => onLookup(retryQuestion)
              : undefined}
            onOpenPdfViewer={onOpenPdfViewer}
          />
        );
      })}

      {loading && <LoadingSkeleton />}

      <div ref={bottomRef} />
    </div>
  );
};
