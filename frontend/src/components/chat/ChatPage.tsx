import React from 'react';
import type { Message } from '../../types/api';
import { WelcomePanel } from './WelcomePanel';
import { MessageList } from './MessageList';
import { ChatComposer } from './ChatComposer';

interface ChatPageProps {
  courseName: string;
  courseId: string;
  suggestedQuestions?: string[];
  messages: Message[];
  loading: boolean;
  canAsk: boolean;
  onSend: (question: string) => void;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({
  courseName,
  courseId,
  suggestedQuestions,
  messages,
  loading,
  canAsk,
  onSend,
  onOpenPdfViewer,
}) => {
  const hasMessages = messages.length > 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50/50">
      <div className="flex-1 overflow-y-auto flex flex-col">
        {!hasMessages ? (
          <div className="flex-1 flex items-center justify-center p-4">
            <WelcomePanel
              courseName={courseName}
              courseId={courseId}
              suggestedQuestions={suggestedQuestions}
              canAsk={canAsk}
              onSelectSuggestion={onSend}
            />
          </div>
        ) : (
          <div className="max-w-3xl w-full mx-auto flex-1 flex flex-col">
            <MessageList
              messages={messages}
              loading={loading}
              onRetry={onSend}
              onOpenPdfViewer={onOpenPdfViewer}
            />
          </div>
        )}
      </div>

      <ChatComposer key={courseId} onSend={onSend} disabled={loading || !canAsk} />
    </div>
  );
};
