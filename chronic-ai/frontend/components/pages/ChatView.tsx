import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, TrendingUp, AlertCircle, Calendar, Activity } from 'lucide-react';
import { mockPatients, mockRecords, mockAlerts } from '@/lib/data/mockData';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatViewProps {
  onOpenPatientEHR?: (patientId: string) => void;
  patientContext?: string | null;
}

export function ChatView({ onOpenPatientEHR, patientContext }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle patient context - auto-ask about patient when context is provided
  useEffect(() => {
    if (patientContext && messages.length === 0) {
      const patient = mockPatients.find(p => p.id === patientContext);
      if (patient) {
        const contextQuestion = `Cho tôi biết tình trạng chi tiết của bệnh nhân ${patient.name}`;
        
        const userMessage: Message = {
          id: Date.now().toString(),
          role: 'user',
          content: contextQuestion,
          timestamp: new Date()
        };

        setMessages([userMessage]);
        setIsTyping(true);

        setTimeout(() => {
          const aiResponse: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: generateAIResponse(contextQuestion),
            timestamp: new Date()
          };
          setMessages(prev => [...prev, aiResponse]);
          setIsTyping(false);
        }, 1000);
      }
    }
  }, [patientContext]);

  const suggestedQuestions = [
    "Có bệnh nhân nào cần chú ý hôm nay không?",
    "Tình trạng của bệnh nhân Trần Thị Bình?",
    "Những bệnh nhân nào có chỉ số đường huyết cao?",
    "Tóm tắt các ca cần chú ý trong tuần"
  ];

  const generateAIResponse = (question: string): string => {
    const lowerQuestion = question.toLowerCase();

    // Check if asking about a specific patient by name
    const patient = mockPatients.find(p => lowerQuestion.includes(p.name.toLowerCase()));
    if (patient) {
      const records = mockRecords.filter(r => r.patientId === patient.id);
      const alerts = mockAlerts.filter(a => a.patientId === patient.id);
      const latestRecord = records[0];
      
      return `**Thông tin bệnh nhân ${patient.name}:**

📋 **Thông tin cơ bản:**
- Tuổi: ${patient.age} tuổi, Giới tính: ${patient.gender === 'M' ? 'Nam' : 'Nữ'}
- Bệnh lý: ${patient.diseases.map(d => {
  if (d === 'hypertension') return 'Cao huyết áp';
  if (d === 'diabetes') return 'Tiểu đường';
  if (d === 'cardiovascular') return 'Tim mạch';
  if (d === 'cancer') return 'Ung thư';
  if (d === 'asthma') return 'Hen suyễn';
  return d;
}).join(', ')}
- Mức độ nguy cơ: **${patient.riskLevel === 'critical' ? '🔴 Nghiêm trọng' : patient.riskLevel === 'high' ? '🟡 Cao' : patient.riskLevel === 'medium' ? '🟠 Trung bình' : '🟢 Thấp'}**
- Lần khám gần nhất: ${new Date(patient.lastVisit).toLocaleDateString('vi-VN')}
- Lịch tái khám: ${new Date(patient.nextFollowUp).toLocaleDateString('vi-VN')}

${latestRecord && latestRecord.details.vitals ? `📊 **Chỉ số sinh hiệu gần nhất:**
${latestRecord.details.vitals.bp ? `- Huyết áp: ${latestRecord.details.vitals.bp}` : ''}
${latestRecord.details.vitals.glucose ? `- Đường huyết: ${latestRecord.details.vitals.glucose} mg/dL` : ''}
${latestRecord.details.vitals.hr ? `- Nhịp tim: ${latestRecord.details.vitals.hr} bpm` : ''}
${latestRecord.details.vitals.weight ? `- Cân nặng: ${latestRecord.details.vitals.weight} kg` : ''}
` : ''}

${alerts.length > 0 ? `🔔 **Cảnh báo gần đây (${alerts.length} cảnh báo):**
${alerts.slice(0, 3).map(a => `- ${a.message} (${format(new Date(a.date), 'dd/MM/yyyy')})`).join('\n')}
` : '✅ **Không có cảnh báo**'}

📋 **Hồ sơ y tế gần đây:**
${records.slice(0, 3).map(r => `- **${r.title}** - ${r.summary} (${format(new Date(r.date), 'dd/MM/yyyy')})`).join('\n')}

${latestRecord && latestRecord.details.diagnoses ? `🩺 **Chẩn đoán:**
${latestRecord.details.diagnoses.map(d => `- ${d}`).join('\n')}
` : ''}

${latestRecord && latestRecord.details.medications ? `💊 **Thuốc đang dùng:**
${latestRecord.details.medications.map(m => `- ${m.name} (${m.dosage}) - ${m.frequency}`).join('\n')}
` : ''}

💡 **Khuyến nghị:** ${patient.riskLevel === 'critical' || patient.riskLevel === 'high' 
  ? 'Cần theo dõi sát các chỉ số quan trọng. Lên lịch tái khám sớm.' 
  : 'Tiếp tục theo dõi và duy trì điều trị hiện tại.'}`;
    }

    // Query about patients needing attention today
    if (lowerQuestion.includes('cần chú ý') && (lowerQuestion.includes('hôm nay') || lowerQuestion.includes('today'))) {
      const criticalPatients = mockPatients.filter(p => p.riskLevel === 'critical' || p.riskLevel === 'high');
      const todayAlerts = mockAlerts.filter(a => {
        const alertDate = new Date(a.date);
        const today = new Date();
        return alertDate.toDateString() === today.toDateString();
      });

      return `**Bệnh nhân cần chú ý hôm nay (${format(new Date(), 'dd/MM/yyyy', { locale: vi })}):**

⚠️ **Bệnh nhân nguy cơ cao:**
${criticalPatients.map((p, i) => `${i + 1}. **${p.name}** - ${p.age} tuổi
   - Bệnh lý: ${p.diseases.map(d => {
     if (d === 'hypertension') return 'Cao huyết áp';
     if (d === 'diabetes') return 'Tiểu đường';
     if (d === 'cardiovascular') return 'Tim mạch';
     if (d === 'cancer') return 'Ung thư';
     if (d === 'asthma') return 'Hen suyễn';
     return d;
   }).join(', ')}
   - Mức độ: ${p.riskLevel === 'critical' ? '🔴 Nghiêm trọng' : '🟡 Cao'}
   - Tái khám: ${p.nextFollowUp}`).join('\n\n')}

🔔 **Cảnh báo hôm nay:** ${todayAlerts.length} cảnh báo
${todayAlerts.slice(0, 3).map(a => `- ${a.message}`).join('\n')}

💡 **Khuyến nghị:** Ưu tiên khám cho bệnh nhân có mức độ nghiêm trọng. Kiểm tra các chỉ số sinh hiệu quan trọng.`;
    }

    // Query about high blood sugar patients
    if (lowerQuestion.includes('đường huyết') || lowerQuestion.includes('glucose') || lowerQuestion.includes('tiểu đường')) {
      const diabeticPatients = mockPatients.filter(p => p.diseases.includes('diabetes'));
      const highGlucoseRecords = mockRecords.filter(r => 
        r.details.vitals?.glucose && parseFloat(r.details.vitals.glucose) > 180
      );

      return `**Bệnh nhân có vấn đề về đường huyết:**

📊 **Bệnh nhân tiểu đường (${diabeticPatients.length} người):**
${diabeticPatients.map((p, i) => {
  const patientRecords = mockRecords.filter(r => r.patientId === p.id && r.details.vitals?.glucose);
  const latestRecord = patientRecords[0];
  return `${i + 1}. **${p.name}** - ${p.age} tuổi
   - Chỉ số gần nhất: ${latestRecord?.details.vitals?.glucose || 'Chưa có dữ liệu'} mg/dL
   - Tình trạng: ${p.riskLevel === 'high' ? '🟡 Cần theo dõi' : '🟢 Ổn định'}
   - Lần khám gần nhất: ${p.lastVisit}`;
}).join('\n\n')}

⚠️ **Lưu ý:**
- Mục tiêu đường huyết lúc đói: 70-130 mg/dL
- Sau ăn 2 giờ: < 180 mg/dL
- HbA1c mục tiêu: < 7%

💡 **Khuyến nghị:** 
- Kiểm tra HbA1c định kỳ 3 tháng/lần
- Theo dõi đường huyết hàng ngày
- Tư vấn chế độ ăn uống và vận động`;
    }

    // Query about weekly summary
    if (lowerQuestion.includes('tuần') || lowerQuestion.includes('week') || lowerQuestion.includes('tóm tắt')) {
      const highRiskPatients = mockPatients.filter(p => p.riskLevel === 'high' || p.riskLevel === 'critical');
      const weekAlerts = mockAlerts.filter(a => a.severity === 'critical' || a.severity === 'warning');
      const recentRecords = mockRecords.filter(r => {
        const recordDate = new Date(r.date);
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        return recordDate > weekAgo;
      });

      return `**Tóm tắt hoạt động tuần này:**

📊 **Tổng quan:**
- Tổng số bệnh nhân: **${mockPatients.length}** người
- Bệnh nhân nguy cơ cao: **${highRiskPatients.length}** người
- Hồ sơ mới trong tuần: **${recentRecords.length}** hồ sơ
- Cảnh báo quan trọng: **${weekAlerts.length}** cảnh báo

⚠️ **Bệnh nhân cần chú ý đặc biệt:**
${highRiskPatients.slice(0, 3).map((p, i) => `${i + 1}. ${p.name} - ${p.diseases.map(d => {
  if (d === 'hypertension') return 'Cao huyết áp';
  if (d === 'diabetes') return 'Tiểu đường';
  if (d === 'cardiovascular') return 'Tim mạch';
  if (d === 'cancer') return 'Ung thư';
  if (d === 'asthma') return 'Hen suyễn';
  return d;
}).join(', ')}`).join('\n')}

📋 **Hoạt động chính:**
${recentRecords.slice(0, 4).map(r => `- ${r.title} cho ${mockPatients.find(p => p.id === r.patientId)?.name} (${format(new Date(r.date), 'dd/MM')})`).join('\n')}

🔔 **Cảnh báo quan trọng:**
${weekAlerts.slice(0, 3).map(a => `- ${a.message} - ${mockPatients.find(p => p.id === a.patientId)?.name}`).join('\n')}

💡 **Khuyến nghị tuần tới:**
- Ưu tiên tái khám cho ${highRiskPatients.length} bệnh nhân nguy cơ cao
- Cập nhật kết quả xét nghiệm định kỳ
- Theo dõi sát các chỉ số sinh hiệu quan trọng`;
    }

    // Query about hypertension
    if (lowerQuestion.includes('cao huyết áp') || lowerQuestion.includes('huyết áp') || lowerQuestion.includes('hypertension')) {
      const hypertensionPatients = mockPatients.filter(p => p.diseases.includes('hypertension'));
      
      return `**Bệnh nhân cao huyết áp:**

📊 **Tổng quan (${hypertensionPatients.length} bệnh nhân):**
${hypertensionPatients.map((p, i) => {
  const records = mockRecords.filter(r => r.patientId === p.id && r.details.vitals?.bp);
  const latestBP = records[0]?.details.vitals?.bp || 'Chưa có dữ liệu';
  return `${i + 1}. **${p.name}** - ${p.age} tuổi, ${p.gender === 'M' ? 'Nam' : 'Nữ'}
   - Huyết áp gần nhất: ${latestBP}
   - Mức độ: ${p.riskLevel === 'critical' ? '🔴 Nghiêm trọng' : p.riskLevel === 'high' ? '🟡 Cao' : '🟢 Trung bình'}
   - Tái khám: ${p.nextFollowUp}`;
}).join('\n\n')}

⚠️ **Tiêu chuẩn huyết áp:**
- Bình thường: < 120/80 mmHg
- Tiền tăng huyết áp: 120-139/80-89 mmHg
- Tăng huyết áp độ 1: 140-159/90-99 mmHg
- Tăng huyết áp độ 2: ≥ 160/100 mmHg

💡 **Khuyến nghị điều trị:**
- Theo dõi huyết áp hàng ngày
- Chế độ ăn ít muối (< 5g/ngày)
- Vận động đều đặn 30 phút/ngày
- Tuân thủ dùng thuốc theo chỉ định`;
    }

    // Default response for other questions
    return `Tôi là trợ lý AI của hệ thống quản lý bệnh nhân mãn tính. Hiện tại tôi có thể giúp bạn:

🔍 **Truy vấn thông tin:**
- Thông tin chi tiết về từng bệnh nhân
- Danh sách bệnh nhân theo mức độ nguy cơ
- Lịch tái khám sắp tới
- Kết quả xét nghiệm và chỉ số sinh hiệu

📊 **Phân tích dữ liệu:**
- Thống kê bệnh nhân theo bệnh lý
- Xu hướng chỉ số sức khỏe
- Cảnh báo và rủi ro
- Tóm tắt hoạt động theo thời gian

💊 **Hỗ trợ lâm sàng:**
- Đề xuất điều trị dựa trên hồ sơ
- Nhắc nhở tái khám và theo dõi
- Phân tích kết quả xét nghiệm
- Tư vấn quản lý bệnh mãn tính

Hãy hỏi tôi về bất kỳ bệnh nhân hoặc vấn đề lâm sàng nào bạn quan tâm!`;
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Simulate AI thinking time
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateAIResponse(input),
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiResponse]);
      setIsTyping(false);
    }, 1000 + Math.random() * 1000);
  };

  const handleSend = (question: string) => {
    setInput(question);
    setTimeout(() => handleSendMessage(), 100);
  };

  const handleSuggestedQuestion = (question: string) => {
    setInput(question);
    setTimeout(() => handleSendMessage(), 100);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Chat Header */}
      <div className="bg-[rgba(255,255,255,0.6)] border-b border-[rgba(255,255,255,0.3)] p-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[16px] flex items-center justify-center">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-[#1e2939]">Trợ lý Bác sĩ AI</h2>
            <p className="text-sm text-[#4a5565]">Hỏi về bất kỳ bệnh nhân nào - Không cần chọn trước</p>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4">
            <div className="w-20 h-20 bg-gradient-to-br from-[#4a9fd8]/20 to-[#2d88c4]/20 rounded-[24px] flex items-center justify-center mb-6">
              <Sparkles className="w-10 h-10 text-[#4a9fd8]" />
            </div>
            <h3 className="text-2xl font-bold text-[#1e2939] mb-3">Trợ lý Bác sĩ AI</h3>
            <p className="text-[#4a5565] mb-8 max-w-md">
              Hỏi về bất kỳ bệnh nhân nào - Không cần chọn trước. AI sẽ tìm 
              đúng các điểm nhấn và truy xuất thông tin lịnh lạnh.
            </p>

            {/* Suggested Questions */}
            <div className="w-full max-w-2xl space-y-3">
              <p className="text-sm font-semibold text-[#4a5565] mb-3">GỢI Ý CÂU HỎI</p>
              {suggestedQuestions.map((question, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestedQuestion(question)}
                  className="w-full text-left px-5 py-4 bg-[rgba(255,255,255,0.6)] hover:bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] text-[#364153] transition-all hover:shadow-[0px_4px_12px_0px_rgba(0,0,0,0.06)]"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6 max-w-4xl mx-auto">
            {messages.map(message => (
              <div
                key={message.id}
                className={`flex gap-4 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <div className={`w-10 h-10 rounded-[14px] flex items-center justify-center flex-shrink-0 ${
                  message.role === 'assistant' 
                    ? 'bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4]' 
                    : 'bg-[rgba(74,159,216,0.2)]'
                }`}>
                  {message.role === 'assistant' ? (
                    <Bot className="w-5 h-5 text-white" />
                  ) : (
                    <User className="w-5 h-5 text-[#4a9fd8]" />
                  )}
                </div>

                {/* Message Content */}
                <div className={`flex-1 ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                  <div className={`inline-block max-w-[85%] px-5 py-4 rounded-[16px] ${
                    message.role === 'assistant'
                      ? 'bg-[rgba(255,255,255,0.6)] border border-[rgba(255,255,255,0.4)]'
                      : 'bg-gradient-to-br from-[#4a9fd8] to-[#2d88c4] text-white'
                  }`}>
                    <div className={`text-sm ${message.role === 'assistant' ? 'text-[#364153]' : 'text-white'} whitespace-pre-wrap`}>
                      {message.content}
                    </div>
                    <div className={`text-xs mt-2 ${message.role === 'assistant' ? 'text-[#99a1af]' : 'text-white/70'}`}>
                      {format(message.timestamp, 'HH:mm', { locale: vi })}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Typing Indicator */}
            {isTyping && (
              <div className="flex gap-4">
                <div className="w-10 h-10 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[14px] flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div className="bg-[rgba(255,255,255,0.6)] border border-[rgba(255,255,255,0.4)] px-5 py-4 rounded-[16px]">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-[#4a9fd8] rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-[#4a9fd8] rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-[#4a9fd8] rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Chat Input */}
      <div className="bg-[rgba(255,255,255,0.6)] border-t border-[rgba(255,255,255,0.3)] p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Hỏi về bệnh nhân, vấn đề lâm sàng hoặc bất kỳ điều gì..."
              className="flex-1 px-5 py-3.5 bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-sm text-[#364153] placeholder:text-[#99a1af]"
              disabled={isTyping}
            />
            <button
              onClick={handleSendMessage}
              disabled={!input.trim() || isTyping}
              className="px-6 py-3.5 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] text-white rounded-[16px] font-medium shadow-[0px_4px_6px_0px_rgba(0,0,0,0.1)] hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send className="w-5 h-5" />
              <span>Gửi</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}