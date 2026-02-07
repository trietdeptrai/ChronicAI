"""Models module."""

from app.models.schemas import (
    # Enums
    UserRole,
    GenderType,
    BloodType,
    TriagePriority,
    ProfileStatus,
    FacilityType,
    VerificationStatus,
    RecordType,
    ConsultationStatus,
    LanguagePref,
    # User models
    UserCreate,
    UserResponse,
    # Patient models
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    # Doctor models
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
    # Facility models
    HealthcareFacilityCreate,
    HealthcareFacilityResponse,
    # Vital signs
    VitalSignsCreate,
    VitalSignsResponse,
    # Medical records
    MedicalRecordCreate,
    MedicalRecordResponse,
    # Consultations
    ConsultationCreate,
    ConsultationUpdate,
    ConsultationResponse,
    # Assignments
    DoctorPatientAssignmentCreate,
    DoctorPatientAssignmentResponse,
)

__all__ = [
    "UserRole",
    "GenderType",
    "BloodType",
    "TriagePriority",
    "ProfileStatus",
    "FacilityType",
    "VerificationStatus",
    "RecordType",
    "ConsultationStatus",
    "LanguagePref",
    "UserCreate",
    "UserResponse",
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "DoctorCreate",
    "DoctorUpdate",
    "DoctorResponse",
    "HealthcareFacilityCreate",
    "HealthcareFacilityResponse",
    "VitalSignsCreate",
    "VitalSignsResponse",
    "MedicalRecordCreate",
    "MedicalRecordResponse",
    "ConsultationCreate",
    "ConsultationUpdate",
    "ConsultationResponse",
    "DoctorPatientAssignmentCreate",
    "DoctorPatientAssignmentResponse",
]
