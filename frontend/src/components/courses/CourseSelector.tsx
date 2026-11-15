import React from 'react';
import { BookOpen, ChevronDown } from 'lucide-react';
import type { Course } from '../../types/api';

interface CourseSelectorProps {
  courses: Course[];
  selectedCourseId: string;
  onSelect: (courseId: string) => void;
  disabled?: boolean;
}

export const CourseSelector: React.FC<CourseSelectorProps> = ({
  courses,
  selectedCourseId,
  onSelect,
  disabled,
}) => {
  const course = courses.find((entry) => entry.course_id === selectedCourseId);
  const documentCount = course?.document_count ?? 0;

  return (
    <div className="space-y-2">
      <label htmlFor="course-select" className="block text-sm font-semibold text-slate-900">
        Học phần đang chọn
      </label>
      <div className="relative rounded-xl border border-slate-200 bg-white shadow-xs transition-colors hover:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-500">
        <div aria-hidden="true" className="flex items-center gap-2.5 px-3 py-2 forced-colors:hidden">
          <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-indigo-50 text-indigo-700">
            <BookOpen className="size-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="line-clamp-2 text-sm leading-5 font-semibold wrap-anywhere text-slate-900">
              {course?.course_name ?? 'Chọn học phần'}
            </div>
            {course && (
              <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-600">
                <span className={`size-1.5 shrink-0 rounded-full ${documentCount > 0 ? 'bg-emerald-600' : 'bg-amber-600'}`} />
                {documentCount > 0 ? `Đã nạp ${documentCount} PDF` : 'Chưa nạp PDF'}
              </div>
            )}
          </div>
          <ChevronDown className="size-4 shrink-0 text-slate-500" />
        </div>
        <select
          id="course-select"
          value={course?.course_id ?? ''}
          onChange={(e) => onSelect(e.target.value)}
          disabled={disabled || courses.length === 0}
          className="absolute inset-0 size-full cursor-pointer opacity-0 disabled:cursor-not-allowed forced-colors:static forced-colors:opacity-100"
        >
          {!course && <option value="" disabled>Chọn học phần</option>}
          {courses.map((course) => (
            <option key={course.course_id} value={course.course_id}>
              {course.course_name} ({course.document_count} PDF)
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};
