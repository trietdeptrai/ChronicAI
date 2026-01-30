import { MedicalRecord } from '@/data/mockData';
import { FileText, TestTube, Image as ImageIcon, Pill, Stethoscope, AlertTriangle } from 'lucide-react';
import { useState } from 'react';

interface MedicalTimelineProps {
  records: MedicalRecord[];
}

export function MedicalTimeline({ records }: MedicalTimelineProps) {
  const [expandedRecord, setExpandedRecord] = useState<string | null>(null);

  const getRecordIcon = (type: MedicalRecord['type']) => {
    const icons = {
      diagnosis: Stethoscope,
      lab: TestTube,
      imaging: ImageIcon,
      prescription: Pill,
      visit: FileText,
      emergency: AlertTriangle,
    };
    return icons[type];
  };

  const getRecordColor = (type: MedicalRecord['type']) => {
    const colors = {
      diagnosis: 'bg-blue-100 text-blue-600',
      lab: 'bg-purple-100 text-purple-600',
      imaging: 'bg-cyan-100 text-cyan-600',
      prescription: 'bg-green-100 text-green-600',
      visit: 'bg-gray-100 text-gray-600',
      emergency: 'bg-red-100 text-red-600',
    };
    return colors[type];
  };

  const getTypeLabel = (type: MedicalRecord['type']) => {
    const labels = {
      diagnosis: 'Chẩn đoán',
      lab: 'Xét nghiệm',
      imaging: 'Hình ảnh',
      prescription: 'Đơn thuốc',
      visit: 'Khám bệnh',
      emergency: 'Cấp cứu',
    };
    return labels[type];
  };

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Dòng thời gian y tế</h3>

        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200"></div>

          <div className="space-y-6">
            {records.map((record, idx) => {
              const Icon = getRecordIcon(record.type);
              const isExpanded = expandedRecord === record.id;

              return (
                <div key={record.id} className="relative">
                  {/* Timeline dot */}
                  <div className={`absolute left-6 w-3 h-3 rounded-full -translate-x-1/2 ${
                    record.type === 'emergency' ? 'bg-red-500' : 'bg-blue-500'
                  }`}></div>

                  <div className="ml-12">
                    <button
                      onClick={() => setExpandedRecord(isExpanded ? null : record.id)}
                      className="w-full text-left bg-white/50 backdrop-blur-sm rounded-2xl shadow-sm border border-white/40 hover:shadow-md transition-all p-5"
                    >
                      <div className="flex items-start gap-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${getRecordColor(record.type)}`}>
                          <Icon className="w-6 h-6" />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-4 mb-2">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-semibold text-gray-900">{record.title}</h4>
                                <span className={`text-xs px-2 py-0.5 rounded ${getRecordColor(record.type)}`}>
                                  {getTypeLabel(record.type)}
                                </span>
                              </div>
                              <p className="text-sm text-gray-500">
                                {new Date(record.date).toLocaleDateString('vi-VN', {
                                  year: 'numeric',
                                  month: 'long',
                                  day: 'numeric',
                                })}
                              </p>
                            </div>
                          </div>

                          <p className="text-gray-700 mb-2">{record.summary}</p>

                          {record.alerts && record.alerts.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2">
                              {record.alerts.map((alert, idx) => (
                                <span key={idx} className="text-xs bg-red-50 text-red-700 px-2 py-1 rounded">
                                  ⚠️ {alert}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="text-sm text-blue-600 font-medium">
                            {isExpanded ? '▲ Thu gọn' : '▼ Xem chi tiết'}
                          </div>
                        </div>
                      </div>

                      {/* Expanded Details */}
                      {isExpanded && (
                        <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
                          {record.details.diagnoses && record.details.diagnoses.length > 0 && (
                            <div>
                              <h5 className="font-semibold text-gray-900 mb-2">Chẩn đoán</h5>
                              <ul className="space-y-1">
                                {record.details.diagnoses.map((d, idx) => (
                                  <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                    <span className="text-blue-600 mt-1">•</span>
                                    <span>{d}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {record.details.labResults && record.details.labResults.length > 0 && (
                            <div>
                              <h5 className="font-semibold text-gray-900 mb-2">Kết quả xét nghiệm</h5>
                              <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="text-left p-2 font-semibold text-gray-700">Xét nghiệm</th>
                                      <th className="text-left p-2 font-semibold text-gray-700">Kết quả</th>
                                      <th className="text-left p-2 font-semibold text-gray-700">Bình thường</th>
                                      <th className="text-left p-2 font-semibold text-gray-700">Trạng thái</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {record.details.labResults.map((lab, idx) => (
                                      <tr key={idx} className="border-t border-gray-100">
                                        <td className="p-2 text-gray-900">{lab.test}</td>
                                        <td className={`p-2 font-semibold ${
                                          lab.status === 'abnormal' ? 'text-red-600' : 'text-gray-900'
                                        }`}>
                                          {lab.value}
                                        </td>
                                        <td className="p-2 text-gray-600">{lab.normal}</td>
                                        <td className="p-2">
                                          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                                            lab.status === 'abnormal'
                                              ? 'bg-red-100 text-red-800'
                                              : 'bg-green-100 text-green-800'
                                          }`}>
                                            {lab.status === 'abnormal' ? 'Bất thường' : 'Bình thường'}
                                          </span>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          {record.details.medications && record.details.medications.length > 0 && (
                            <div>
                              <h5 className="font-semibold text-gray-900 mb-2">Thuốc</h5>
                              <div className="space-y-2">
                                {record.details.medications.map((med, idx) => (
                                  <div key={idx} className="bg-green-50 rounded-lg p-3">
                                    <div className="font-semibold text-gray-900">{med.name}</div>
                                    <div className="text-sm text-gray-600">
                                      Liều: {med.dosage} • {med.frequency}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {record.details.findings && record.details.findings.length > 0 && (
                            <div>
                              <h5 className="font-semibold text-gray-900 mb-2">Phát hiện</h5>
                              <ul className="space-y-1">
                                {record.details.findings.map((f, idx) => (
                                  <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                    <span className="text-cyan-600 mt-1">•</span>
                                    <span>{f}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {record.details.imageUrl && (
                            <div>
                              <h5 className="font-semibold text-gray-900 mb-2">Hình ảnh y tế</h5>
                              <img
                                src={record.details.imageUrl}
                                alt={record.title}
                                className="w-full max-w-md rounded-lg border border-gray-200"
                              />
                            </div>
                          )}

                          {record.details.recommendations && record.details.recommendations.length > 0 && (
                            <div>
                              <h5 className="font-semibold text-gray-900 mb-2">Khuyến nghị</h5>
                              <ul className="space-y-1">
                                {record.details.recommendations.map((r, idx) => (
                                  <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                    <span className="text-blue-600 mt-1">→</span>
                                    <span>{r}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}