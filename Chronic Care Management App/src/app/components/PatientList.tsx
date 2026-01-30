import { Patient, getDiseaseInfo } from '@/data/mockData';
import { Search, AlertTriangle, TrendingUp } from 'lucide-react';
import { useState } from 'react';

interface PatientListProps {
  patients: Patient[];
  selectedPatientId: string | null;
  onSelectPatient: (id: string) => void;
}

export function PatientList({ patients, selectedPatientId, onSelectPatient }: PatientListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPatients = patients.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getRiskBadge = (risk: Patient['riskLevel']) => {
    const styles = {
      low: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800',
    };
    const labels = {
      low: 'Thấp',
      medium: 'TB',
      high: 'Cao',
      critical: 'Nghiêm trọng',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${styles[risk]}`}>
        {labels[risk]}
      </span>
    );
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-[rgba(229,231,235,0.5)]">
        <h2 className="font-bold text-[#364153] mb-3">Patient List</h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#99a1af]" />
          <input
            type="text"
            placeholder="Search patients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 bg-[rgba(255,255,255,0.6)] text-sm placeholder:text-[rgba(10,10,10,0.5)]"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-1">
          {filteredPatients.map(patient => (
            <button
              key={patient.id}
              onClick={() => onSelectPatient(patient.id)}
              className={`w-full text-left p-3 rounded-[16px] transition-all ${
                selectedPatientId === patient.id
                  ? 'bg-[rgba(255,255,255,0.8)] shadow-[0px_4px_12px_0px_rgba(0,0,0,0.06)] border border-white'
                  : 'hover:bg-[rgba(255,255,255,0.4)]'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">{patient.name}</h3>
                    {patient.riskLevel === 'critical' && (
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                  <p className="text-xs text-gray-600">
                    {patient.age} tuổi • {patient.gender === 'M' ? 'Nam' : 'Nữ'}
                  </p>
                </div>
                {getRiskBadge(patient.riskLevel)}
              </div>

              <div className="flex flex-wrap gap-1 mb-2">
                {patient.diseases.map(disease => {
                  const info = getDiseaseInfo(disease);
                  return (
                    <span
                      key={disease}
                      className={`text-xs px-2 py-0.5 rounded ${info.color}`}
                    >
                      {info.icon} {info.name}
                    </span>
                  );
                })}
              </div>

              <div className="flex items-center gap-1 text-xs text-gray-500">
                <TrendingUp className="w-3 h-3" />
                <span>Tái khám: {new Date(patient.nextFollowUp).toLocaleDateString('vi-VN')}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-600 space-y-1">
          <div className="flex justify-between">
            <span>Tổng bệnh nhân:</span>
            <span className="font-semibold">{patients.length}</span>
          </div>
          <div className="flex justify-between">
            <span>Nguy cơ cao/nghiêm trọng:</span>
            <span className="font-semibold text-red-600">
              {patients.filter(p => p.riskLevel === 'high' || p.riskLevel === 'critical').length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}