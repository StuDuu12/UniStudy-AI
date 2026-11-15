import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  CornerDownLeft,
  Sparkles,
  Bot,
  Cpu,
  ChevronDown,
  ChevronRight,
  Key,
  Eye,
  EyeOff,
  Check,
  X,
  ExternalLink,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import type { AnswerStyle, ModelProvider } from '../../types/api';

const MAX_QUESTION_LENGTH = 1000;

interface SubModelOption {
  id: string;
  name: string;
  badge: string;
  badgeType: 'emerald' | 'indigo' | 'violet' | 'blue' | 'slate' | 'amber' | 'rose';
  specs: string;
  description: string;
  isJudgeRecommended?: boolean;
}

const LOCAL_MODELS: SubModelOption[] = [
  {
    id: 'lookup',
    name: 'Tra cứu giáo trình (Offline)',
    badge: 'Khuyên dùng cho Giám khảo',
    badgeType: 'emerald',
    specs: '100% CPU • Không cần cài đặt • <50ms',
    description: 'Trích xuất & tổng hợp chính xác từ PDF. Chắc chắn hoạt động trên mọi máy tính chấm thi.',
    isJudgeRecommended: true,
  },
  {
    id: 'qwen3.5:4b',
    name: 'Qwen 3.5 (4B)',
    badge: 'Ưu tiên số 1 • Cân bằng tốt nhất',
    badgeType: 'emerald',
    specs: '4B • ~2.7-3 GB VRAM/RAM • Q4_K_M ~2.74 GB',
    description: 'Model chính cho chatbot tiếng Việt: hội thoại, hỏi đáp tài liệu, tóm tắt, viết nội dung và hỗ trợ lập trình.',
  },
  {
    id: 'qwen3.5:2b',
    name: 'Qwen 3.5 (2B)',
    badge: 'Rất nhẹ • Chạy mượt CPU',
    badgeType: 'blue',
    specs: '2B • ~1.3-1.8 GB RAM • Tiết kiệm tài nguyên',
    description: 'Phù hợp chatbot chạy CPU hoặc máy có ít VRAM, đặc biệt với FAQ, trả lời ngắn, phân loại yêu cầu và chatbot nội bộ đơn giản.',
  },
  {
    id: 'qwen3.5:9b',
    name: 'Qwen 3.5 (9B)',
    badge: 'Chất lượng cao • Suy luận tốt',
    badgeType: 'violet',
    specs: '9B • ~5.5-6.5 GB • Nên chọn khi có GPU >= 12GB',
    description: 'Phù hợp chatbot giáo dục, giải thích kiến thức và các tác vụ đòi hỏi suy luận tốt hơn. Chat tiếng Việt, lập trình tốt hơn.',
  },
  {
    id: 'gemma4:e4b',
    name: 'Gemma 4 E4B IT',
    badge: 'Đa phương thức • Chất lượng cao',
    badgeType: 'indigo',
    specs: '4.5B hiệu dụng • ~4-5 GB RAM • Google DeepMind',
    description: 'Phù hợp nếu chatbot cần tiếp nhận hình ảnh, văn bản hoặc âm thanh. Cần cân nhắc lượng RAM thực tế cao hơn so với một model 4B thuần văn bản.',
  },
];

const GEMINI_MODELS: SubModelOption[] = [
  {
    id: 'gemini-3.8-flash',
    name: 'Gemini 3.8 Flash',
    badge: 'Flash mạnh • Tác vụ phức tạp',
    badgeType: 'indigo',
    specs: 'Google AI 2026 • Xử lý đa tầng',
    description: 'Flash mạnh mẽ nhất thế hệ 2026 của Google, xử lý mượt mà tài liệu học tập phức tạp.',
  },
  {
    id: 'gemini-3.7-flash',
    name: 'Gemini 3.7 Flash',
    badge: 'Lập trình & AI Agent',
    badgeType: 'violet',
    specs: 'Google AI • Code & Thuật toán',
    description: 'Tối ưu hóa chuyên sâu cho giải thuật, lập trình mã nguồn và quy trình AI Agent.',
  },
  {
    id: 'gemini-3.6-flash',
    name: 'Gemini 3.6 Flash',
    badge: 'Đa năng • Tốc độ tốt',
    badgeType: 'emerald',
    specs: 'Google AI • Cân bằng hoàn hảo',
    description: 'Chat đa năng với tốc độ xử lý nhanh, cân bằng xuất sắc giữa thời gian phản hồi và độ chính xác.',
  },
  {
    id: 'gemini-3.5-flash',
    name: 'Gemini 3.5 Flash',
    badge: 'Tác vụ phổ thông',
    badgeType: 'blue',
    specs: 'Google AI • Phổ thông ổn định',
    description: 'Mô hình phổ thông ổn định, đáp ứng nhanh các câu hỏi tra cứu khái niệm và ôn tập kiến thức.',
  },
  {
    id: 'gemini-3.5-flash-lite',
    name: 'Gemini 3.5 Flash-Lite',
    badge: 'Siêu tiết kiệm',
    badgeType: 'slate',
    specs: 'Google AI Lite • Độ trễ cực thấp',
    description: 'Phiên bản siêu nhẹ, phản hồi tức thì và tối ưu hóa tối đa chi phí cũng như quota sử dụng.',
  },
  {
    id: 'gemini-3.1-pro-preview',
    name: 'Gemini 3.1 Pro Preview',
    badge: 'Suy luận sâu • Preview',
    badgeType: 'amber',
    specs: 'Google AI Pro • Phân tích chuyên sâu',
    description: 'Bản xem trước suy luận chuyên sâu, thích hợp cho các bài toán phân tích học thuật đa chiều.',
  },
];

const CHATGPT_MODELS: SubModelOption[] = [
  {
    id: 'gpt-6-astra',
    name: 'GPT-6 Astra',
    badge: 'Cao cấp nhất • Flagship 2026',
    badgeType: 'rose',
    specs: 'OpenAI 2026 • Suy luận chuyên sâu',
    description: 'Mô hình cao cấp và thông minh nhất của OpenAI 2026, khả năng phân tích học thuật và suy luận xuất sắc.',
  },
  {
    id: 'gpt-6.1-sol',
    name: 'GPT-6.1 Sol',
    badge: 'Toán học & Lập trình',
    badgeType: 'violet',
    specs: 'OpenAI Reasoning • Phân tích phức tạp',
    description: 'Mô hình chuyên biệt cho toán học, khoa học máy tính, lập trình và giải quyết các bài toán logic hóc búa.',
  },
  {
    id: 'gpt-6.1-terra',
    name: 'GPT-6.1 Terra',
    badge: 'Chat đa năng • Chuẩn sư phạm',
    badgeType: 'indigo',
    specs: 'OpenAI Balanced • Đa năng & Diễn giải',
    description: 'Mô hình cân bằng hoàn hảo, trình bày bài giảng rõ ràng, súc tích và hỗ trợ hiểu tài liệu trực quan.',
  },
  {
    id: 'gpt-6-luna',
    name: 'GPT-6 Luna',
    badge: 'Chat nhanh • Chi phí thấp',
    badgeType: 'emerald',
    specs: 'OpenAI Economy • Tối ưu chi phí',
    description: 'Mô hình gọn nhẹ với chi phí thấp và tốc độ trả lời chớp nhoáng, tối ưu cho học tập thường ngày.',
  },
];

const BADGE_STYLES: Record<string, string> = {
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200/80',
  indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200/80',
  violet: 'bg-violet-50 text-violet-700 border-violet-200/80',
  blue: 'bg-blue-50 text-blue-700 border-blue-200/80',
  slate: 'bg-slate-100 text-slate-700 border-slate-200',
  amber: 'bg-amber-50 text-amber-700 border-amber-200/80',
  rose: 'bg-rose-50 text-rose-700 border-rose-200/80',
};

interface ChatComposerProps {
  onSend: (question: string) => void;
  answerStyle: AnswerStyle;
  onAnswerStyleChange: (style: AnswerStyle) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSend,
  answerStyle,
  onAnswerStyleChange,
  disabled,
  placeholder = 'Nhập câu hỏi về bài giảng, khái niệm trong học phần...',
}) => {
  const [question, setQuestion] = useState('');
  const [model, setModel] = useState<ModelProvider>(() => {
    return (localStorage.getItem('unistudy_selected_model') as ModelProvider) || 'local';
  });
  const [modelName, setModelName] = useState<string>(() => {
    return localStorage.getItem('unistudy_selected_model_name') || 'lookup';
  });
  const [geminiKey, setGeminiKey] = useState<string>(() => {
    return localStorage.getItem('unistudy_gemini_key') || '';
  });
  const [chatgptKey, setChatgptKey] = useState<string>(() => {
    return localStorage.getItem('unistudy_chatgpt_key') || '';
  });

  const [menuOpen, setMenuOpen] = useState(false);
  const [hoveredCategory, setHoveredCategory] = useState<ModelProvider>(model);
  const [showKeyGemini, setShowKeyGemini] = useState(false);
  const [showKeyChatgpt, setShowKeyChatgpt] = useState(false);
  const [keySavedNotice, setKeySavedNotice] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const canSubmit = question.trim().length > 0 && !disabled;
  const isLookup = model === 'local' && modelName === 'lookup';

  // Whenever menu opens, sync preview pane to currently selected model
  useEffect(() => {
    if (menuOpen) {
      setHoveredCategory(model);
    }
  }, [menuOpen, model]);

  // Persist selections
  const handleSelectSubModel = (provider: ModelProvider, subModelId: string) => {
    setModel(provider);
    setModelName(subModelId);
    setHoveredCategory(provider);
    localStorage.setItem('unistudy_selected_model', provider);
    localStorage.setItem('unistudy_selected_model_name', subModelId);
    setMenuOpen(false);
  };

  const handleSaveGeminiKey = (val: string) => {
    setGeminiKey(val);
    localStorage.setItem('unistudy_gemini_key', val);
    setKeySavedNotice('Đã lưu API Key Gemini');
    setTimeout(() => setKeySavedNotice(null), 2500);
  };

  const handleSaveChatgptKey = (val: string) => {
    setChatgptKey(val);
    localStorage.setItem('unistudy_chatgpt_key', val);
    setKeySavedNotice('Đã lưu API Key ChatGPT');
    setTimeout(() => setKeySavedNotice(null), 2500);
  };

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [question]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!canSubmit) return;

    onSend(question.trim());
    setQuestion('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const hasKey = (provider: ModelProvider) => {
    if (provider === 'gemini') return Boolean(geminiKey.trim());
    if (provider === 'chatgpt') return Boolean(chatgptKey.trim());
    return true;
  };

  const getTriggerLabel = () => {
    if (model === 'local') {
      const found = LOCAL_MODELS.find((m) => m.id === modelName);
      if (!found || found.id === 'lookup') return 'Local: Tra cứu giáo trình';
      return `Local: ${found.name}`;
    }
    if (model === 'gemini') {
      const found = GEMINI_MODELS.find((m) => m.id === modelName);
      return `Gemini: ${found ? found.name.replace('Gemini ', '') : (modelName || '3.8 Flash')}`;
    }
    if (model === 'chatgpt') {
      const found = CHATGPT_MODELS.find((m) => m.id === modelName);
      return `ChatGPT: ${found ? found.name.replace('OpenAI ', '') : (modelName || 'GPT-6 Astra')}`;
    }
    return 'Chọn mô hình';
  };

  return (
    <div className="border-t border-slate-200/80 bg-white/95 backdrop-blur-xs p-3 sm:p-4 shrink-0">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto space-y-2">
        {/* Model Switcher Bar */}
        <div className="flex items-center justify-between px-1">
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200/70 border border-slate-200/90 text-xs font-semibold text-slate-800 transition-colors shadow-2xs cursor-pointer"
              title="Nhấp để đổi mô hình xử lý hoặc nhập API Key"
              aria-expanded={menuOpen}
            >
              {model === 'local' && (
                <>
                  <Cpu className="w-3.5 h-3.5 text-slate-700" />
                  <span>{getTriggerLabel()}</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-500" title="Chạy cục bộ sẵn sàng" />
                </>
              )}
              {model === 'gemini' && (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  <span>{getTriggerLabel()}</span>
                  <span
                    className={`w-2 h-2 rounded-full ${hasKey('gemini') ? 'bg-emerald-500' : 'bg-amber-400 animate-pulse'}`}
                    title={hasKey('gemini') ? 'Đã có API Key' : 'Chưa nhập API Key'}
                  />
                </>
              )}
              {model === 'chatgpt' && (
                <>
                  <Bot className="w-3.5 h-3.5 text-emerald-600" />
                  <span>{getTriggerLabel()}</span>
                  <span
                    className={`w-2 h-2 rounded-full ${hasKey('chatgpt') ? 'bg-emerald-500' : 'bg-amber-400 animate-pulse'}`}
                    title={hasKey('chatgpt') ? 'Đã có API Key' : 'Chưa nhập API Key'}
                  />
                </>
              )}
              <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Hierarchical Multi-Level Model Menu */}
            {menuOpen && (
              <div className="absolute bottom-full left-0 mb-2 w-[340px] sm:w-[600px] h-[480px] rounded-2xl bg-white border border-slate-200 shadow-2xl p-0 z-50 animate-in fade-in zoom-in-95 duration-150 overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/70 shrink-0">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Chọn mô hình xử lý & cấu hình API</span>
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Rê chuột vào nhóm mô hình để xem danh sách chi tiết
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMenuOpen(false)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {keySavedNotice && (
                  <div className="mx-4 mt-2 p-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] flex items-center gap-1.5 animate-in fade-in shrink-0">
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{keySavedNotice}</span>
                  </div>
                )}

                {/* 2-Column Multi-level Layout with stable fixed height */}
                <div className="flex-1 flex flex-col sm:flex-row min-h-0 overflow-hidden">
                  {/* Left Column: Categories / Providers */}
                  <div className="w-full sm:w-48 bg-slate-50/95 border-b sm:border-b-0 sm:border-r border-slate-200 p-2.5 flex flex-col justify-between shrink-0 h-full overflow-y-auto">
                    <div className="space-y-1.5">
                      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
                        Nhóm mô hình
                      </div>

                      {/* Local Category */}
                      <div
                        onMouseEnter={() => setHoveredCategory('local')}
                        onClick={() => setHoveredCategory('local')}
                        className={`flex items-center justify-between p-2.5 rounded-xl cursor-pointer transition-all border ${
                          hoveredCategory === 'local'
                            ? 'bg-indigo-50/90 border-indigo-300 text-indigo-950 font-bold shadow-2xs'
                            : 'border-transparent hover:bg-slate-100/90 text-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Cpu className={`w-4 h-4 ${hoveredCategory === 'local' ? 'text-indigo-600' : 'text-slate-500'}`} />
                          <div className="text-left">
                            <div className="text-xs">Local Máy</div>
                            <div className="text-[10px] text-slate-400 font-normal">Offline / Ollama</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {model === 'local' && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-md font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              Đang chọn
                            </span>
                          )}
                          <ChevronRight className={`w-3.5 h-3.5 ${hoveredCategory === 'local' ? 'text-indigo-600 translate-x-0.5' : 'text-slate-400'} transition-transform`} />
                        </div>
                      </div>

                      {/* Gemini Category */}
                      <div
                        onMouseEnter={() => setHoveredCategory('gemini')}
                        onClick={() => setHoveredCategory('gemini')}
                        className={`flex items-center justify-between p-2.5 rounded-xl cursor-pointer transition-all border ${
                          hoveredCategory === 'gemini'
                            ? 'bg-indigo-50/90 border-indigo-300 text-indigo-950 font-bold shadow-2xs'
                            : 'border-transparent hover:bg-slate-100/90 text-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Sparkles className={`w-4 h-4 ${hoveredCategory === 'gemini' ? 'text-indigo-600' : 'text-slate-500'}`} />
                          <div className="text-left">
                            <div className="text-xs">Google Gemini</div>
                            <div className="text-[10px] text-slate-400 font-normal">Đám mây Google</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {model === 'gemini' && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-md font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              Đang chọn
                            </span>
                          )}
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${hasKey('gemini') ? 'bg-emerald-500' : 'bg-amber-400'}`}
                            title={hasKey('gemini') ? 'Đã có key' : 'Cần nhập key'}
                          />
                          <ChevronRight className={`w-3.5 h-3.5 ${hoveredCategory === 'gemini' ? 'text-indigo-600 translate-x-0.5' : 'text-slate-400'} transition-transform`} />
                        </div>
                      </div>

                      {/* ChatGPT Category */}
                      <div
                        onMouseEnter={() => setHoveredCategory('chatgpt')}
                        onClick={() => setHoveredCategory('chatgpt')}
                        className={`flex items-center justify-between p-2.5 rounded-xl cursor-pointer transition-all border ${
                          hoveredCategory === 'chatgpt'
                            ? 'bg-indigo-50/90 border-indigo-300 text-indigo-950 font-bold shadow-2xs'
                            : 'border-transparent hover:bg-slate-100/90 text-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Bot className={`w-4 h-4 ${hoveredCategory === 'chatgpt' ? 'text-emerald-600' : 'text-slate-500'}`} />
                          <div className="text-left">
                            <div className="text-xs">OpenAI ChatGPT</div>
                            <div className="text-[10px] text-slate-400 font-normal">Đám mây OpenAI</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {model === 'chatgpt' && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-md font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              Đang chọn
                            </span>
                          )}
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${hasKey('chatgpt') ? 'bg-emerald-500' : 'bg-amber-400'}`}
                            title={hasKey('chatgpt') ? 'Đã có key' : 'Cần nhập key'}
                          />
                          <ChevronRight className={`w-3.5 h-3.5 ${hoveredCategory === 'chatgpt' ? 'text-indigo-600 translate-x-0.5' : 'text-slate-400'} transition-transform`} />
                        </div>
                      </div>
                    </div>

                    {/* Quick Info Box at bottom of left column */}
                    <div className="pt-3 px-1 text-[10px] text-slate-400 leading-tight border-t border-slate-200/70">
                      Rê chuột để đổi xem chi tiết mô hình tức thì.
                    </div>
                  </div>

                  {/* Right Column: Sub-models & API Key Details */}
                  <div className="flex-1 h-full overflow-y-auto p-4 space-y-3 pb-8 bg-white">
                    {/* Content for LOCAL */}
                    {hoveredCategory === 'local' && (
                      <div className="space-y-2.5">
                        <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                          <div>
                            <span className="text-xs font-bold text-slate-900">Mô hình Chạy Cục Bộ (Local)</span>
                            <p className="text-[11px] text-slate-500">
                              Chạy trên máy cá nhân hoặc máy chấm thi của Giám khảo
                            </p>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                            {LOCAL_MODELS.length} tùy chọn
                          </span>
                        </div>

                        {/* Sub-models list */}
                        <div className="space-y-1.5">
                          {LOCAL_MODELS.map((item) => {
                            const isSelected = model === 'local' && modelName === item.id;
                            return (
                              <div
                                key={item.id}
                                role="button"
                                tabIndex={0}
                                onClick={() => handleSelectSubModel('local', item.id)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSelectSubModel('local', item.id)}
                                className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                                  isSelected
                                    ? 'border-indigo-600 bg-indigo-50/50 shadow-2xs'
                                    : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50/70'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-bold text-slate-900">{item.name}</span>
                                    {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600 stroke-[2.5]" />}
                                  </div>
                                  <span
                                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                                      BADGE_STYLES[item.badgeType] || BADGE_STYLES.slate
                                    }`}
                                  >
                                    {item.badge}
                                  </span>
                                </div>
                                <div className="text-[10px] text-indigo-600 font-medium mt-0.5">{item.specs}</div>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{item.description}</p>
                              </div>
                            );
                          })}
                        </div>

                        {/* Local explanation note */}
                        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[10px] text-slate-500 space-y-1">
                          <div className="font-semibold text-slate-700 flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Bảo đảm máy Giám khảo:</span>
                          </div>
                          <div>
                            Nếu máy Giám khảo chưa cài Ollama, chế độ <strong>Tra cứu giáo trình</strong> sẽ tự động chạy 100% bằng CPU, không cần tải thêm bất kỳ file mô hình nào.
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Content for GEMINI */}
                    {hoveredCategory === 'gemini' && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                          <div>
                            <span className="text-xs font-bold text-slate-900">Google Gemini API</span>
                            <p className="text-[11px] text-slate-500">Mô hình trí tuệ nhân tạo thế hệ mới của Google</p>
                          </div>
                          {hasKey('gemini') ? (
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Đã có API Key
                            </span>
                          ) : (
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              Cần nhập Key
                            </span>
                          )}
                        </div>

                        {/* API Key Box */}
                        <div className="p-2.5 rounded-xl bg-indigo-50/50 border border-indigo-100 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <label className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
                              <Key className="w-3 h-3 text-indigo-600" />
                              <span>Gemini API Key:</span>
                            </label>
                            <a
                              href="https://aistudio.google.com/app/apikey"
                              target="_blank"
                              rel="noreferrer"
                              className="text-[10px] text-indigo-600 hover:underline flex items-center gap-0.5 font-medium"
                            >
                              Lấy key miễn phí <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                          <div className="relative flex items-center">
                            <input
                              type={showKeyGemini ? 'text' : 'password'}
                              value={geminiKey}
                              onChange={(e) => handleSaveGeminiKey(e.target.value)}
                              placeholder="Dán mã khóa AIzaSy..."
                              className="w-full text-xs bg-white border border-slate-300 rounded-lg py-1.5 pl-2.5 pr-8 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono shadow-2xs"
                            />
                            <button
                              type="button"
                              onClick={() => setShowKeyGemini(!showKeyGemini)}
                              className="absolute right-2 text-slate-400 hover:text-slate-600 p-0.5 cursor-pointer"
                              title={showKeyGemini ? 'Ẩn khóa' : 'Hiện khóa'}
                            >
                              {showKeyGemini ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>

                        {/* Sub-models list */}
                        <div className="space-y-1.5">
                          {GEMINI_MODELS.map((item) => {
                            const isSelected = model === 'gemini' && modelName === item.id;
                            return (
                              <div
                                key={item.id}
                                role="button"
                                tabIndex={0}
                                onClick={() => handleSelectSubModel('gemini', item.id)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSelectSubModel('gemini', item.id)}
                                className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                                  isSelected
                                    ? 'border-indigo-600 bg-indigo-50/50 shadow-2xs'
                                    : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50/70'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-bold text-slate-900">{item.name}</span>
                                    {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600 stroke-[2.5]" />}
                                  </div>
                                  <span
                                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                                      BADGE_STYLES[item.badgeType] || BADGE_STYLES.slate
                                    }`}
                                  >
                                    {item.badge}
                                  </span>
                                </div>
                                <div className="text-[10px] text-indigo-600 font-medium mt-0.5">{item.specs}</div>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{item.description}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Content for CHATGPT */}
                    {hoveredCategory === 'chatgpt' && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                          <div>
                            <span className="text-xs font-bold text-slate-900">OpenAI ChatGPT API</span>
                            <p className="text-[11px] text-slate-500">Mô hình GPT ngôn ngữ tự nhiên từ OpenAI</p>
                          </div>
                          {hasKey('chatgpt') ? (
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Đã có API Key
                            </span>
                          ) : (
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              Cần nhập Key
                            </span>
                          )}
                        </div>

                        {/* API Key Box */}
                        <div className="p-2.5 rounded-xl bg-emerald-50/50 border border-emerald-100 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <label className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
                              <Key className="w-3 h-3 text-emerald-600" />
                              <span>OpenAI API Key:</span>
                            </label>
                            <a
                              href="https://platform.openai.com/api-keys"
                              target="_blank"
                              rel="noreferrer"
                              className="text-[10px] text-emerald-700 hover:underline flex items-center gap-0.5 font-medium"
                            >
                              Lấy key tại OpenAI <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                          <div className="relative flex items-center">
                            <input
                              type={showKeyChatgpt ? 'text' : 'password'}
                              value={chatgptKey}
                              onChange={(e) => handleSaveChatgptKey(e.target.value)}
                              placeholder="Dán mã khóa sk-..."
                              className="w-full text-xs bg-white border border-slate-300 rounded-lg py-1.5 pl-2.5 pr-8 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono shadow-2xs"
                            />
                            <button
                              type="button"
                              onClick={() => setShowKeyChatgpt(!showKeyChatgpt)}
                              className="absolute right-2 text-slate-400 hover:text-slate-600 p-0.5 cursor-pointer"
                              title={showKeyChatgpt ? 'Ẩn khóa' : 'Hiện khóa'}
                            >
                              {showKeyChatgpt ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>

                        {/* Sub-models list */}
                        <div className="space-y-1.5">
                          {CHATGPT_MODELS.map((item) => {
                            const isSelected = model === 'chatgpt' && modelName === item.id;
                            return (
                              <div
                                key={item.id}
                                role="button"
                                tabIndex={0}
                                onClick={() => handleSelectSubModel('chatgpt', item.id)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSelectSubModel('chatgpt', item.id)}
                                className={`p-2.5 rounded-xl border text-left cursor-pointer transition-all ${
                                  isSelected
                                    ? 'border-indigo-600 bg-indigo-50/50 shadow-2xs'
                                    : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50/70'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-bold text-slate-900">{item.name}</span>
                                    {isSelected && <Check className="w-3.5 h-3.5 text-indigo-600 stroke-[2.5]" />}
                                  </div>
                                  <span
                                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                                      BADGE_STYLES[item.badgeType] || BADGE_STYLES.slate
                                    }`}
                                  >
                                    {item.badge}
                                  </span>
                                </div>
                                <div className="text-[10px] text-indigo-600 font-medium mt-0.5">{item.specs}</div>
                                <p className="text-[11px] text-slate-600 mt-1 leading-snug">{item.description}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <span className="text-[11px] text-slate-400 font-medium">
            {model === 'local' && (
              modelName === 'lookup'
                ? 'Chọn mô hình AI để giải thích hoặc soạn câu ôn tập.'
                : `Ollama Local (${modelName})`
            )}
            {model === 'gemini' && (hasKey('gemini') ? `Google Gemini (${modelName})` : 'Chưa nhập API Key Gemini')}
            {model === 'chatgpt' && (hasKey('chatgpt') ? `OpenAI ChatGPT (${modelName})` : 'Chưa nhập API Key ChatGPT')}
          </span>
        </div>

        {!isLookup && (
          <label className="flex flex-wrap items-center gap-2 px-1 text-xs text-slate-600">
            <span>Kiểu trả lời AI</span>
            <select
              value={answerStyle}
              onChange={(event) => onAnswerStyleChange(event.target.value as AnswerStyle)}
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-slate-800 focus:border-indigo-500 focus:outline-none"
            >
              <option value="auto">Theo câu hỏi</option>
              <option value="detailed">Giải thích chi tiết</option>
              <option value="comparison">So sánh</option>
              <option value="example">Ví dụ minh họa</option>
              <option value="review">Câu hỏi ôn tập</option>
            </select>
          </label>
        )}

        {/* Question Textarea Box */}
        <div className="relative flex items-end bg-slate-50 border border-slate-200 rounded-2xl shadow-2xs focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:bg-white transition-all p-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={question}
            maxLength={MAX_QUESTION_LENGTH}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            aria-label="Câu hỏi"
            className="w-full bg-transparent resize-none border-0 focus:outline-none focus:ring-0 text-sm text-slate-900 placeholder-slate-400 py-1.5 px-2.5 max-h-40 min-h-[40px] leading-relaxed selection:bg-indigo-100"
          />

          <div className="flex items-center gap-2 pl-2 pb-1 shrink-0">
            <span className="hidden sm:inline-flex items-center text-[10px] text-slate-400 font-mono select-none pr-1">
              <CornerDownLeft className="w-2.5 h-2.5 mr-0.5 opacity-60" /> Enter
            </span>
            <button
              type="submit"
              disabled={!canSubmit}
              aria-label="Gửi câu hỏi"
              className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white disabled:text-slate-400 flex items-center justify-center transition-all duration-150 shadow-xs disabled:shadow-none cursor-pointer disabled:cursor-not-allowed hover:scale-105 active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Footer info & helper */}
        <div className="flex items-center justify-between px-2 text-[11px] text-slate-400">
          <span className="inline-flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-500/70" />
            <span>Đối chiếu trực tiếp với giáo trình PDF đã nạp</span>
          </span>
          {question.length > 700 && (
            <span className="font-mono">
              {question.length} / {MAX_QUESTION_LENGTH}
            </span>
          )}
        </div>
      </form>
    </div>
  );
};
