import { useState, useEffect } from 'react';
import { mockPatients, mockRecords } from '@/lib/data/mockData';
import { PatientList } from '@/components/pages/PatientList';
import { PatientDetail } from '@/components/pages/PatientDetail';
import { Stethoscope } from 'lucide-react';

interface PatientsPageProps {
  onOpenPatientEHR?: (patientId: string) => void;
  onAskAIAboutPatient?: (patientId: string) => void;
  preSelectedPatientId?: string | null;
}

export function PatientsPage({ onOpenPatientEHR, onAskAIAboutPatient, preSelectedPatientId }: PatientsPageProps) {
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(preSelectedPatientId || null);

  // Update selected patient when preSelectedPatientId changes
  useEffect(() => {
    if (preSelectedPatientId) {
      setSelectedPatientId(preSelectedPatientId);
    }
  }, [preSelectedPatientId]);

  const handleSelectPatient = (patientId: string) => {
    setSelectedPatientId(patientId);
    if (onOpenPatientEHR) {
      onOpenPatientEHR(patientId);
    }
  };

  return (
    <div className="grid grid-cols-[400px_1fr] gap-6 h-full">
      {/* Patient List */}
      <div className="bg-white/60 backdrop-blur-md rounded-3xl border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
        <PatientList
          patients={mockPatients}
          selectedPatientId={selectedPatientId}
          onSelectPatient={handleSelectPatient}
        />
      </div>

      {/* Patient Detail */}
      <div className="bg-white/60 backdrop-blur-md rounded-3xl border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden">
        {selectedPatientId ? (
          <PatientDetail
            patientId={selectedPatientId}
            records={mockRecords.filter(r => r.patientId === selectedPatientId)}
            isDoctor={true}
            onAskAIAboutPatient={onAskAIAboutPatient}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Stethoscope className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p className="text-lg">Select a patient to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}