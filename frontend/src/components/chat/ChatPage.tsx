import React, { useState } from 'react';
import type { AnswerStyle, Course, Message, SendQuestion } from '../../types/api';
import { WelcomePanel } from './WelcomePanel';
import { MessageList } from './MessageList';
import { ChatComposer } from './ChatComposer';

interface ChatPageProps {
  courseName: string;
  courseId: string;
  suggestedQuestions?: string[];
  course?: Course;
  messages: Message[];
  loading: boolean;
  canAsk: boolean;
  onSend: SendQuestion;
  onOpenPdfViewer?: (docId: string, docName: string, page: number, totalPages?: number) => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({
  courseName,
  courseId,
  suggestedQuestions,
  course,
  messages,
  loading,
  canAsk,
  onSend,
  onOpenPdfViewer,
}) => {
  const hasMessages = messages.length > 0;
  const [answerStyle, setAnswerStyle] = useState<AnswerStyle>('auto');

  function sendWithSelectedModel(question: string) {
    if (loading || !canAsk) return;
    const selected = localStorage.getItem('unistudy_selected_model');
    const provider = selected === 'gemini' || selected === 'chatgpt' ? selected : 'local';
    const model = localStorage.getItem('unistudy_selected_model_name') || (provider === 'local' ? 'lookup' : undefined);
    const apiKey = provider === 'local' ? undefined : localStorage.getItem(`unistudy_${provider}_key`)?.trim() || undefined;
    onSend(question, provider, model, apiKey, { answerStyle: model === 'lookup' ? 'auto' : answerStyle });
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50/50">
      <div className="flex-1 overflow-y-auto flex flex-col">
        {!hasMessages ? (
          <div className="flex-1 flex items-center justify-center p-4">
            <WelcomePanel
              courseName={courseName}
              courseId={courseId}
              suggestedQuestions={suggestedQuestions}
              course={course}
              canAsk={canAsk}
              onSelectSuggestion={sendWithSelectedModel}
            />
          </div>
        ) : (
          <div className="max-w-3xl w-full mx-auto flex-1 flex flex-col">
            <MessageList
              messages={messages}
              loading={loading}
              onRetry={sendWithSelectedModel}
              onLookup={(question) => onSend(question, 'local', 'lookup')}
              onOpenPdfViewer={onOpenPdfViewer}
            />
          </div>
        )}
      </div>

      <ChatComposer
        key={courseId}
        onSend={sendWithSelectedModel}
        disabled={loading || !canAsk}
        answerStyle={answerStyle}
        onAnswerStyleChange={setAnswerStyle}
      />
    </div>
  );
};
