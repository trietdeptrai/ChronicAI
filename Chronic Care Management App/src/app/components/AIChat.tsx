import { useState, useRef, useEffect } from 'react';
import { getAIResponse, getPatientAIResponse } from '@/data/mockData';
import { Send, Bot, User, AlertTriangle, Sparkles } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AIChatProps {
  patientId: string;
  isDoctor: boolean;
}

export function AIChat({ patientId, isDoctor }: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: isDoctor
        ? `Xin chào! Tôi là trợ lý AI hỗ trợ lâm sàng.\n\nTôi có thể giúp bạn:\n- Phân tích hồ sơ bệnh án\n- Đánh giá các chỉ số xét nghiệm\n- Giải thích kết quả hình ảnh và ECG\n- So sánh diễn tiến bệnh\n- Gợi ý theo dõi và tái khám\n\nHãy hỏi tôi về bệnh nhân này!`
        : `Xin chào! Tôi là trợ lý AI sức khỏe của bạn.\n\nTôi có thể giúp bạn hiểu:\n- Bệnh của bạn là gì\n- Thuốc có tác dụng như thế nào\n- Kết quả xét nghiệm nghĩa là gì\n- Chế độ ăn uống và sinh hoạt\n- Dấu hiệu cảnh báo cần chú ý\n\nHãy hỏi tôi bất cứ điều gì bạn thắc mắc!`,
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Simulate AI thinking time
    setTimeout(() => {
      const aiResponse = isDoctor
        ? getAIResponse(input, patientId)
        : getPatientAIResponse(input, patientId);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: aiResponse,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);
    }, 1000 + Math.random() * 1000);
  };

  const suggestedQuestions = isDoctor
    ? [
        'Hôm nay bệnh nhân có cao huyết áp không?',
        'Kết quả HbA1c gần nhất là bao nhiêu?',
        'Có dấu hiệu gì cần can thiệp ngay không?',
        'So với lần trước, tình trạng có xấu hơn không?',
      ]
    : [
        'Cao huyết áp là gì?',
        'Thuốc của tôi có tác dụng gì?',
        'Tôi nên ăn uống như thế nào?',
        'Khi nào cần gặp bác sĩ gấp?',
      ];

  return (
    <div className="flex flex-col h-full">
      {/* Warning Banner */}
      <div className={`${isDoctor ? 'bg-[#4A9FD8]/10 border-[#4A9FD8]/20' : 'bg-amber-50/60 border-amber-200/40'} backdrop-blur-sm border-b px-6 py-3`}>
        <div className="flex items-center gap-2 text-sm">
          <AlertTriangle className={`w-4 h-4 ${isDoctor ? 'text-[#4A9FD8]' : 'text-amber-600'}`} />
          <p className={isDoctor ? 'text-gray-700' : 'text-amber-800'}>
            {isDoctor
              ? 'AI hỗ trợ phân tích - Không thay thế quyết định lâm sàng của bác sĩ'
              : 'AI chỉ cung cấp thông tin tham khảo - Mọi quyết định điều trị cần tham khảo bác sĩ'}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map(message => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] flex items-center justify-center flex-shrink-0 shadow-md">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}

            <div
              className={`max-w-2xl rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4] text-white shadow-md'
                  : 'bg-white/60 backdrop-blur-sm border border-white/40 text-gray-900 shadow-sm'
              }`}
            >
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {message.content}
              </div>
              <div
                className={`text-xs mt-2 ${
                  message.role === 'user' ? 'text-purple-100' : 'text-gray-500'
                }`}
              >
                {message.timestamp.toLocaleTimeString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>

            {message.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-white" />
              </div>
            )}
          </div>
        ))}

        {isTyping && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] flex items-center justify-center flex-shrink-0 shadow-md">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-white/60 backdrop-blur-sm border border-white/40 rounded-2xl px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions */}
      {messages.length === 1 && (
        <div className="px-6 py-3 bg-white/30 backdrop-blur-sm border-t border-gray-200/30">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#4A9FD8]" />
            <span className="text-sm font-semibold text-gray-700">Gợi ý câu hỏi:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => setInput(q)}
                className="text-sm px-3 py-1.5 bg-white/60 backdrop-blur-sm border border-white/40 rounded-xl hover:bg-white/80 hover:border-[#4A9FD8]/30 transition-colors text-left shadow-sm"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-6 bg-white/40 backdrop-blur-md border-t border-white/30">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder={isDoctor ? 'Hỏi AI về bệnh nhân này...' : 'Hỏi AI về sức khỏe của bạn...'}
            className="flex-1 px-4 py-3 border border-white/40 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#4A9FD8]/30 bg-white/60 backdrop-blur-sm shadow-sm text-sm"
            disabled={isTyping}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="px-6 py-3 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4] text-white rounded-2xl hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-md"
          >
            <Send className="w-5 h-5" />
            <span className="font-medium">Gửi</span>
          </button>
        </div>
      </div>
    </div>
  );
}