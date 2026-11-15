import React, { useState } from 'react';
import type { useChat } from '../../hooks/useChat';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { ChatPage } from '../chat/ChatPage';
import { PdfViewerModal } from '../pdf/PdfViewerModal';

type AppShellProps = ReturnType<typeof useChat>;

export const AppShell: React.FC<AppShellProps> = ({
  courses,
  selectedCourseId,
  selectedCourse,
  documents,
  documentsLoading,
  documentsError,
  conversations,
  activeConversationId,
  historyStorageError,
  messages,
  loading,
  canAsk,
  catalogStatus,
  catalogError,
  onReloadCourses,
  onSelectCourse,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
  onSendQuestion,
  onAddCourse,
  onAddDocuments,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pdfViewer, setPdfViewer] = useState<{
    isOpen: boolean;
    docId: string;
    docName: string;
    page: number;
    totalPages?: number;
  }>({
    isOpen: false,
    docId: '',
    docName: '',
    page: 1,
    totalPages: 0,
  });

  const handleOpenPdfViewer = (
    docId: string,
    docName: string,
    page: number,
    totalPages?: number
  ) => {
    const doc = documents.find((d) => d.document_id === docId);
    const resolvedTotal = totalPages || doc?.page_count || 0;
    setPdfViewer({
      isOpen: true,
      docId,
      docName,
      page: page || 1,
      totalPages: resolvedTotal,
    });
  };

  const handleClosePdfViewer = () => {
    setPdfViewer((prev) => ({ ...prev, isOpen: false }));
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <AppSidebar
        courses={courses}
        selectedCourseId={selectedCourseId}
        documents={documents}
        documentsLoading={documentsLoading}
        documentsError={documentsError}
        catalogStatus={catalogStatus}
        catalogError={catalogError}
        conversations={conversations}
        activeConversationId={activeConversationId}
        historyStorageError={historyStorageError}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onReloadCourses={onReloadCourses}
        onSelectCourse={(id) => {
          onSelectCourse(id);
          setSidebarOpen(false);
        }}
        onAddCourse={onAddCourse}
        onAddDocuments={onAddDocuments}
        onNewConversation={() => {
          onNewConversation();
          setSidebarOpen(false);
        }}
        onSelectConversation={(id) => {
          onSelectConversation(id);
          setSidebarOpen(false);
        }}
        onDeleteConversation={onDeleteConversation}
        onRenameConversation={onRenameConversation}
        onOpenPdfViewer={handleOpenPdfViewer}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <AppHeader
          courseName={selectedCourse?.course_name || 'Học phần'}
          documentCount={selectedCourse?.document_count ?? 0}
          catalogStatus={catalogStatus}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(true)}
        />

        <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <ChatPage
            key={`${selectedCourseId}:${activeConversationId ?? 'draft'}`}
            courseName={selectedCourse?.course_name || ''}
            courseId={selectedCourseId}
            suggestedQuestions={selectedCourse?.suggested_questions}
            messages={messages}
            loading={loading}
            canAsk={canAsk}
            onSend={onSendQuestion}
            onOpenPdfViewer={handleOpenPdfViewer}
          />
        </main>
      </div>

      {/* Full Interactive PDF Viewer Modal */}
      <PdfViewerModal
        isOpen={pdfViewer.isOpen}
        onClose={handleClosePdfViewer}
        documentId={pdfViewer.docId}
        documentName={pdfViewer.docName}
        page={pdfViewer.page}
        initialTotalPages={pdfViewer.totalPages}
      />
    </div>
  );
};
