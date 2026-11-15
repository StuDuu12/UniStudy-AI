import React from 'react';
import { BookOpen, Sparkles, CheckCircle, FileText, ArrowRight } from 'lucide-react';
import type { Course } from '../../types/api';

interface WelcomePanelProps {
  courseName: string;
  courseId: string;
  canAsk: boolean;
  onSelectSuggestion: (question: string) => void;
  suggestedQuestions?: string[];
  course?: Course;
}

const COURSE_SUGGESTIONS: Record<string, string[]> = {
  tin_hoc_dai_cuong: [
    'Hệ điều hành có những chức năng gì?',
    'Cấu trúc cơ bản của máy tính gồm những thành phần nào?',
    'Phần mềm hệ thống khác phần mềm ứng dụng ở điểm nào?',
    'Các thao tác định dạng văn bản cơ bản trong Word là gì?',
  ],
  software_testing: [
    'Phân vùng tương đương là gì?',
    'Phân vùng tương đương khác phân tích giá trị biên ở đâu?',
    'Một ca kiểm thử hộp đen cần ghi những thông tin nào?',
    'Nên thử những giá trị biên nào cho ô điểm nguyên từ 0 đến 100?',
  ],
  algorithm_analysis: [
    'Big O là gì và biểu diễn cận trên như thế nào?',
    'Quy tắc tuần tự khi phân tích thời gian tính là gì?',
    'Trường hợp cơ sở có vai trò gì trong hệ thức truy hồi của đệ quy?',
    'Vì sao sắp xếp trộn có độ phức tạp O(n log n)?',
  ],
  toan_roi_rac: [
    'Định nghĩa mệnh đề trong logic mệnh đề là gì?',
    'Các phép toán tập hợp cơ bản gồm những phép toán nào?',
    'Đại số Boole có những tính chất và tiên đề cơ bản nào?',
    'Định nghĩa đồ thị liên thông và đường đi Euler?',
    'Đường một nét Euler là gì?',
  ],
  thu_thap_phan_tich_yeu_cau: [
    'Yêu cầu chức năng khác yêu cầu phi chức năng như thế nào?',
    'Các kỹ thuật phổ biến để khám phá yêu cầu phần mềm?',
    'Biểu đồ Use Case dùng để mô hình hóa khía cạnh nào của hệ thống?',
    'Tại sao cần tài liệu hóa yêu cầu bằng ngôn ngữ tự nhiên rõ ràng?',
    'Yêu cầu phi chức năng quy định những tính chất và ràng buộc nào?',
  ],
};

export const WelcomePanel: React.FC<WelcomePanelProps> = ({
  courseName,
  courseId,
  canAsk,
  onSelectSuggestion,
  suggestedQuestions,
  course,
}) => {
  const dynamicQuestions = (suggestedQuestions && suggestedQuestions.length > 0)
    ? suggestedQuestions
    : (course?.suggested_questions && course.suggested_questions.length > 0)
      ? course.suggested_questions
      : COURSE_SUGGESTIONS[courseId] ?? [];
  const suggestions = canAsk ? dynamicQuestions : [];

  return (
    <div className="py-8 px-4 max-w-2xl mx-auto text-center space-y-6 animate-in fade-in duration-200">
      {/* Brand Hero Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 text-xs font-semibold shadow-2xs">
        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
        <span>Trợ lý học tập thông minh UniStudy AI</span>
      </div>

      {/* Main Headline */}
      <div className="space-y-2.5">
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          {courseName || 'Học phần đại học'}
        </h2>
        <p className="text-sm text-slate-600 max-w-lg mx-auto leading-relaxed">
          {canAsk
            ? 'Tra cứu PDF hoặc chọn mô hình AI để giải thích bài, minh họa bằng ví dụ và tạo câu hỏi ôn tập.'
            : courseId
              ? 'Chưa có tài liệu trong học phần này. Hãy thêm tệp PDF từ thanh bên để bắt đầu tra cứu.'
              : 'Hãy chọn một học phần ở thanh bên trái hoặc tạo học phần mới để bắt đầu ôn tập.'}
        </p>
      </div>

      {/* Core Capability Pills */}
      <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white border border-slate-200/80 text-xs text-slate-700 font-medium shadow-2xs">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
          <span>Trích dẫn chuẩn trang PDF</span>
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white border border-slate-200/80 text-xs text-slate-700 font-medium shadow-2xs">
          <FileText className="w-3.5 h-3.5 text-indigo-600" />
          <span>Đọc toàn văn trực tiếp</span>
        </span>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white border border-slate-200/80 text-xs text-slate-700 font-medium shadow-2xs">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Báo khi thiếu căn cứ</span>
        </span>
      </div>

      {/* Suggested Questions */}
      {suggestions.length > 0 && (
        <div className="pt-4 text-left space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
              <span>Gợi ý câu hỏi từ giáo trình</span>
            </span>
            <span className="text-[11px] font-normal lowercase text-slate-400">chọn để hỏi ngay</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {suggestions.map((question, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectSuggestion(question)}
                className="text-left p-3.5 rounded-xl bg-white border border-slate-200/80 hover:border-indigo-400 hover:shadow-xs transition-all text-xs text-slate-700 hover:text-indigo-950 group cursor-pointer flex flex-col justify-between gap-2"
              >
                <div className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-md bg-slate-100 group-hover:bg-indigo-50 group-hover:text-indigo-600 text-slate-400 text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5 transition-colors">
                    {idx + 1}
                  </span>
                  <span className="leading-snug font-medium text-slate-800 group-hover:text-indigo-900 transition-colors">
                    {question}
                  </span>
                </div>
                <div className="flex items-center justify-end text-[10px] text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity font-semibold gap-1 pt-1">
                  <span>Hỏi câu này</span>
                  <ArrowRight className="w-3 h-3" />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
