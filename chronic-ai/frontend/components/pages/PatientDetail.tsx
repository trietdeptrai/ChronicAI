import { useState } from 'react';
import { mockPatients, MedicalRecord, getDiseaseInfo } from '@/lib/data/mockData';
import { MedicalTimeline } from '@/components/pages/MedicalTimeline';
import { AIChat } from '@/components/pages/AIChat';
import { DocumentUpload } from '@/components/pages/DocumentUpload';
import { User, Calendar, Activity, Upload, MessageSquare, FileText, AlertCircle, Bot } from 'lucide-react';

interface PatientDetailProps {
  patientId: string;
  records: MedicalRecord[];
  isDoctor: boolean;
  onAskAIAboutPatient?: (patientId: string) => void;
}

export function PatientDetail({ patientId, records, isDoctor, onAskAIAboutPatient }: PatientDetailProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'chat' | 'upload'>('overview');
  const patient = mockPatients.find(p => p.id === patientId);

  if (!patient) return null;

  const latestRecord = records[0];
  const criticalAlerts = records.flatMap(r => r.alerts || []);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Patient Header */}
      <div className="p-6 border-b border-gray-200/30">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] rounded-2xl flex items-center justify-center shadow-lg">
              <User className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-1">{patient.name}</h2>
              <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                <span>{patient.age} tuổi</span>
                <span>•</span>
                <span>{patient.gender === 'M' ? 'Nam' : 'Nữ'}</span>
                <span>•</span>
                <span className={`font-semibold ${
                  patient.riskLevel === 'critical' ? 'text-red-600' :
                  patient.riskLevel === 'high' ? 'text-orange-600' :
                  patient.riskLevel === 'medium' ? 'text-yellow-600' :
                  'text-green-600'
                }`}>
                  {patient.riskLevel === 'critical' ? 'Nguy cơ nghiêm trọng' :
                   patient.riskLevel === 'high' ? 'Nguy cơ cao' :
                   patient.riskLevel === 'medium' ? 'Nguy cơ trung bình' :
                   'Nguy cơ thấp'}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {patient.diseases.map(disease => {
                  const info = getDiseaseInfo(disease);
                  return (
                    <span
                      key={disease}
                      className={`text-sm px-3 py-1 rounded-full ${info.color}`}
                    >
                      {info.icon} {info.name}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="text-right text-sm">
            <div className="text-gray-600 mb-1">
              Khám gần nhất: {new Date(patient.lastVisit).toLocaleDateString('vi-VN')}
            </div>
            <div className="font-semibold text-[#4A9FD8]">
              Tái khám: {new Date(patient.nextFollowUp).toLocaleDateString('vi-VN')}
            </div>
          </div>
        </div>

        {/* Critical Alerts */}
        {criticalAlerts.length > 0 && (
          <div className="bg-red-50/80 backdrop-blur-sm border border-red-200/50 rounded-2xl p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h4 className="font-semibold text-red-900 mb-1 text-sm">Cảnh báo quan trọng</h4>
                <ul className="space-y-1">
                  {criticalAlerts.slice(0, 3).map((alert, idx) => (
                    <li key={idx} className="text-sm text-red-800">• {alert}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="px-6 border-b border-gray-200/30">
        <div className="flex gap-1 -mb-px">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
              activeTab === 'overview'
                ? 'text-[#4A9FD8]'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>Tổng quan</span>
            </div>
            {activeTab === 'overview' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4]"></div>
            )}
          </button>

          <button
            onClick={() => setActiveTab('timeline')}
            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
              activeTab === 'timeline'
                ? 'text-[#4A9FD8]'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              <span>Dòng thời gian</span>
            </div>
            {activeTab === 'timeline' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4]"></div>
            )}
          </button>

          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
              activeTab === 'chat'
                ? 'text-[#4A9FD8]'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              <span>Trợ lý AI</span>
            </div>
            {activeTab === 'chat' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4]"></div>
            )}
          </button>

          {isDoctor && (
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-4 py-3 text-sm font-medium transition-colors relative ${
                activeTab === 'upload'
                  ? 'text-[#4A9FD8]'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <div className="flex items-center gap-2">
                <Upload className="w-4 h-4" />
                <span>Tải lên tài liệu</span>
              </div>
              {activeTab === 'upload' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4]"></div>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' && (
          <div className="p-6 space-y-4">
            {/* Ask AI Button */}
            {isDoctor && onAskAIAboutPatient && (
              <button
                onClick={() => onAskAIAboutPatient(patientId)}
                className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4] text-white rounded-2xl font-semibold hover:shadow-lg transition-all group"
              >
                <Bot className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span>Hỏi AI về bệnh án của {patient.name}</span>
              </button>
            )}

            {/* Latest Visit Summary */}
            {latestRecord && (
              <div className="bg-white/40 backdrop-blur-sm rounded-2xl p-5 border border-white/40">
                <h3 className="font-bold text-gray-900 mb-4">Khám gần nhất</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-gray-900">{latestRecord.title}</h4>
                      <span className="text-sm text-gray-500">
                        {new Date(latestRecord.date).toLocaleDateString('vi-VN')}
                      </span>
                    </div>
                    <p className="text-gray-700">{latestRecord.summary}</p>
                  </div>

                  {latestRecord.details.diagnoses && (
                    <div>
                      <h5 className="text-sm font-semibold text-gray-700 mb-2">Chẩn đoán:</h5>
                      <ul className="space-y-1">
                        {latestRecord.details.diagnoses.map((d, idx) => (
                          <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                            <span className="text-blue-600 mt-1">•</span>
                            <span>{d}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {latestRecord.details.vitals && (
                    <div>
                      <h5 className="text-sm font-semibold text-gray-700 mb-2">Sinh hiệu:</h5>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {latestRecord.details.vitals.bp && (
                          <div className="bg-blue-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 mb-1">Huyết áp</div>
                            <div className="font-semibold text-gray-900">{latestRecord.details.vitals.bp}</div>
                          </div>
                        )}
                        {latestRecord.details.vitals.glucose && (
                          <div className="bg-purple-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 mb-1">Đường huyết</div>
                            <div className="font-semibold text-gray-900">{latestRecord.details.vitals.glucose}</div>
                          </div>
                        )}
                        {latestRecord.details.vitals.hr && (
                          <div className="bg-red-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 mb-1">Nhịp tim</div>
                            <div className="font-semibold text-gray-900">{latestRecord.details.vitals.hr} bpm</div>
                          </div>
                        )}
                        {latestRecord.details.vitals.weight && (
                          <div className="bg-green-50 rounded-lg p-3">
                            <div className="text-xs text-gray-600 mb-1">Cân nặng</div>
                            <div className="font-semibold text-gray-900">{latestRecord.details.vitals.weight} kg</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {latestRecord.details.medications && (
                    <div>
                      <h5 className="text-sm font-semibold text-gray-700 mb-2">Thuốc đang dùng:</h5>
                      <div className="space-y-2">
                        {latestRecord.details.medications.map((med, idx) => (
                          <div key={idx} className="bg-gray-50 rounded-lg p-3">
                            <div className="font-semibold text-gray-900">{med.name}</div>
                            <div className="text-sm text-gray-600">
                              {med.dosage} • {med.frequency}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Quick Stats */}
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-white/70 backdrop-blur-xl rounded-xl shadow-lg border border-purple-200/50 p-4">
                <div className="text-sm text-gray-600 mb-1">Tổng hồ sơ</div>
                <div className="text-2xl font-bold text-gray-900">{records.length}</div>
              </div>
              <div className="bg-white/70 backdrop-blur-xl rounded-xl shadow-lg border border-purple-200/50 p-4">
                <div className="text-sm text-gray-600 mb-1">Xét nghiệm</div>
                <div className="text-2xl font-bold text-gray-900">
                  {records.filter(r => r.type === 'lab').length}
                </div>
              </div>
              <div className="bg-white/70 backdrop-blur-xl rounded-xl shadow-lg border border-purple-200/50 p-4">
                <div className="text-sm text-gray-600 mb-1">Hình ảnh</div>
                <div className="text-2xl font-bold text-gray-900">
                  {records.filter(r => r.type === 'imaging').length}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'timeline' && (
          <MedicalTimeline records={records} />
        )}

        {activeTab === 'chat' && (
          <AIChat patientId={patientId} isDoctor={isDoctor} />
        )}

        {activeTab === 'upload' && isDoctor && (
          <DocumentUpload patientId={patientId} />
        )}
      </div>
    </div>
  );
}
