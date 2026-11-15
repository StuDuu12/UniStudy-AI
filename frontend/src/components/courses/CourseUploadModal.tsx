import React, { useState, useRef } from 'react';
import { X, Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { createCourse } from '../../services/api';
import type { Course } from '../../types/api';

interface CourseUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCourseCreated: (course: Course) => void;
}

export const CourseUploadModal: React.FC<CourseUploadModalProps> = ({
  isOpen,
  onClose,
  onCourseCreated,
}) => {
  const [courseName, setCourseName] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      const pdfFiles = files.filter((f) => f.name.toLowerCase().endsWith('.pdf'));
      if (pdfFiles.length === 0) {
        setErrorMessage('Chỉ chấp nhận tệp định dạng PDF.');
        return;
      }
      if (pdfFiles.length > 5) {
        setErrorMessage('Tối đa 5 tệp PDF cho mỗi học phần.');
        setSelectedFiles(pdfFiles.slice(0, 5));
        return;
      }
      setSelectedFiles(pdfFiles);
      setErrorMessage(null);
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!courseName.trim()) {
      setErrorMessage('Vui lòng nhập tên học phần.');
      return;
    }
    if (selectedFiles.length === 0) {
      setErrorMessage('Vui lòng chọn ít nhất 1 tệp PDF.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const newCourse = await createCourse(courseName.trim(), selectedFiles);
      onCourseCreated(newCourse);
      onClose();
      // Reset form
      setCourseName('');
      setSelectedFiles([]);
    } catch (err: any) {
      setErrorMessage(err.message || 'Không thể tạo học phần. Vui lòng kiểm tra lại.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-2xs animate-in fade-in duration-150">
      <div
        className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Thêm học phần & Nạp PDF</h3>
              <p className="text-xs text-slate-500">Tải lên tài liệu PDF để tra cứu và giải thích</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label htmlFor="course-name-input" className="block text-xs font-semibold text-slate-700 mb-1.5">
              Tên học phần <span className="text-rose-500">*</span>
            </label>
            <input
              id="course-name-input"
              type="text"
              value={courseName}
              onChange={(e) => setCourseName(e.target.value)}
              disabled={isSubmitting}
              placeholder="VD: Mạng máy tính, Cơ sở dữ liệu, Kiến trúc máy tính..."
              className="w-full text-sm border border-slate-300 rounded-xl px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Tệp PDF tài liệu <span className="text-rose-500">*</span>
            </label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-200 hover:border-indigo-400 rounded-xl p-4 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-indigo-50/20"
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,application/pdf"
                onChange={handleFileChange}
                disabled={isSubmitting}
                className="hidden"
              />
              <FileText className="w-8 h-8 text-indigo-500 mx-auto mb-2 opacity-80" />
              <p className="text-xs font-medium text-slate-700">
                Nhấp để chọn tệp PDF học liệu
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                Tối đa 5 tệp PDF có văn bản (mỗi tệp không quá 20 MB)
              </p>
            </div>
          </div>

          {/* Selected file list */}
          {selectedFiles.length > 0 && (
            <div className="space-y-1.5 max-h-36 overflow-y-auto">
              {selectedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-100 text-xs text-slate-800"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span className="truncate font-medium">{file.name}</span>
                    <span className="text-slate-400 text-[10px] shrink-0">
                      ({(file.size / 1024 / 1024).toFixed(1)} MB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(idx)}
                    disabled={isSubmitting}
                    className="text-slate-400 hover:text-rose-600 p-0.5"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Submit */}
          <div className="pt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !courseName.trim() || selectedFiles.length === 0}
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white disabled:text-slate-400 transition-all shadow-xs flex items-center gap-1.5 cursor-pointer disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang xử lý PDF...</span>
                </>
              ) : (
                <span>Tạo học phần</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
