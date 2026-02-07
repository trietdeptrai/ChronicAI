"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DoctorDashboard } from "@/components/pages/DoctorDashboard";
import { PatientDashboard } from "@/components/pages/PatientDashboard";

export default function DashboardPage() {
  const [userRole, setUserRole] = useState<"doctor" | "patient" | null>(null);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("p1");
  const router = useRouter();

  useEffect(() => {
    // Get user role from localStorage
    const role = localStorage.getItem("userRole") as "doctor" | "patient" | null;
    if (!role) {
      router.push("/");
    } else {
      setUserRole(role);
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("userRole");
    router.push("/");
  };

  if (!userRole) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <>
      {userRole === "doctor" ? (
        <DoctorDashboard onLogout={handleLogout} />
      ) : (
        <PatientDashboard 
          onLogout={handleLogout} 
          patientId={selectedPatientId} 
        />
      )}
    </>
  );
}
