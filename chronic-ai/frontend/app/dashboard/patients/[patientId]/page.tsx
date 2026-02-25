/**
 * Patient detail page with profile photo upload
 */
"use client"

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth, useDashboardLanguage, type DashboardLanguage } from "@/contexts"
import {
    PageHeader,
    LoadingOverlay,
    RecordAIAnalysis,
    UploadProgressOverlay,
} from "@/components/shared"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/alert-dialog"
import {
    usePatient,
    usePatientRecords,
    usePatientVitals,
    useCreateVitalSign,
    useUpdateVitalSign,
    useDeleteVitalSign,
    useExportMedicalHistory,
    useExportVitalSigns,
    useImportMedicalHistoryPreview,
    useImportVitalSignsPreview,
    useImportPatientText,
    useExportPatientText,
    useUpdatePatient,
    useUploadPatientPhoto,
    useUploadPatientRecordImage,
    useUpdatePatientRecord,
    useDeletePatientRecord,
    useGeneratePatientSummary,
} from "@/lib/hooks"
import type {
    MedicalRecord,
    MedicalRecordAIAnalysis,
    MedicalHistoryImportPreview,
    Patient,
    PatientUpdateInput,
    PatientTextImportStatusResponse,
    VitalSign,
    VitalSignInput,
} from "@/types"
import { Activity, ArrowLeft, FileText, Upload, Sparkles, RotateCw, Clock, Monitor } from "lucide-react"
import { toast } from "sonner"
import ReactMarkdown from "react-markdown"

type ImagingRecordType =
    | "lab"
    | "xray"
    | "ecg"
    | "ct"
    | "mri"

type TextExportFormat = "json" | "pdf"

type MedicalHistoryFieldKey =
    | "chronic_conditions"
    | "past_surgeries"
    | "hospitalizations"
    | "medications_history"
    | "allergies"
    | "psychiatric_history"
    | "family_history_of_chronic_conditions"
    | "family_history_of_mental_health_conditions"
    | "family_history_of_genetic_conditions"
    | "vaccines_administered"
    | "vaccines_due"
    | "previous_treatments"
    | "physiotherapy"
    | "other_relevant_treatments"

type MedicalHistoryFormState = Record<MedicalHistoryFieldKey, string[]>

type MedicalHistoryFieldDefinition = {
    key: MedicalHistoryFieldKey
    label: Record<DashboardLanguage, string>
    placeholder: Record<DashboardLanguage, string>
}

type MedicalHistoryFieldGroup = {
    title: Record<DashboardLanguage, string>
    fields: MedicalHistoryFieldDefinition[]
}

type ExportUiText = {
    formatAriaLabel: string
    filterAriaLabel: string
    exportTextButton: string
    exportFilesButton: string
    importTextButton: string
    exporting: string
    importing: string
    exportHint: string
    missingPatientDataId: string
    missingPatientFilesId: string
    missingPatientImportId: string
    invalidImportFileType: string
    exportTextSuccessJson: string
    exportTextSuccessPdf: string
    exportFilesSuccess: string
    importSuccess: string
    exportTextFailed: string
    exportFilesFailed: string
    importFailed: string
}

type PatientDetailUiText = {
    locale: string
    backButton: string
    pageTitle: string
    loadingPatient: string
    loadPatientErrorTitle: string
    loadPatientErrorHint: string
    photoCardTitle: string
    patientPhotoUploadLabel: string
    photoUploadFailed: string
    photoUpdateSuccess: string
    photoUploadButton: string
    uploadingLabel: string
    savingLabel: string
    updatingLabel: string
    deletingLabel: string
    vitalsCardTitle: string
    vitalRecordedAtLabel: string
    vitalSourceLabel: string
    vitalBpSystolicLabel: string
    vitalBpDiastolicLabel: string
    vitalHeartRateLabel: string
    vitalSpo2Label: string
    vitalTemperatureLabel: string
    vitalWeightLabel: string
    vitalBloodGlucoseLabel: string
    vitalGlucoseTimingLabel: string
    vitalNotesLabel: string
    vitalNotesPlaceholder: string
    vitalSaveFailed: string
    vitalSaveButton: string
    vitalSaveSuccess: string
    recentHistoryLabel: string
    recordCountSuffix: string
    vitalsLoading: string
    vitalsLoadFailed: string
    vitalsEmpty: string
    medicalRecordsTitle: string
    medicalRecordsSubtitle: string
    recordsLoading: string
    recordsLoadFailed: string
    recordsEmpty: string
    recordVerifiedBadge: string
    editButton: string
    deleteButton: string
    downloadPdf: string
    noAttachment: string
    imagingCardTitle: string
    imagingTypeLabel: string
    recordTitleLabel: string
    recordTitlePlaceholder: string
    recordFileLabel: string
    recordUploadFailed: string
    recordUploadButton: string
    postUploadDialogTitle: string
    postUploadDialogHint: string
    postUploadNoAnalysis: string
    doctorCommentPlaceholder: string
    skipButton: string
    saveCommentButton: string
    editDialogTitle: string
    editRecordTitleLabel: string
    editRecordTypeLabel: string
    editRecordFileLabel: string
    editRecordFileHint: string
    editRecordCommentLabel: string
    cancelButton: string
    saveChangesButton: string
    deleteDialogTitle: string
    deleteDialogDescription: string
    activeRecordFallbackTitle: string
    activeRecordNoImage: string
    uploadProgressTitle: string
    uploadCompleted: string
    uploadFailed: string
    uploadStageUpload: string
    uploadStageValidate: string
    uploadStageEcgEmbedding: string
    uploadStageEcgClassifier: string
    uploadStageImageAnalysis: string
    uploadStageAiAnalysis: string
    uploadStageSave: string
    errors: {
        missingPatientId: string
        choosePhotoFirst: string
        invalidPhotoFile: string
        chooseImagingFileFirst: string
        invalidImagingFile: string
        recordUploadFallback: string
        saveDoctorCommentFailed: string
        replacementFileInvalid: string
        updateRecordFailed: string
        deleteRecordFailed: string
        enterAtLeastOneVital: string
    }
    success: {
        recordUploadSuccess: string
        saveDoctorCommentSuccess: string
        updateRecordSuccess: string
        deleteRecordSuccess: string
    }
    options: {
        imagingType: Record<ImagingRecordType, string>
        recordType: Record<string, string>
        vitalSource: Record<string, string>
        glucoseTiming: Record<string, string>
    }
    summaryCardTitle: string
    summaryCardSubtitle: string
    summaryGenerateButton: string
    summaryRegenerateButton: string
    summaryGenerating: string
    summaryGeneratingHint: string
    summaryError: string
    summaryTimestamp: string
    summaryModel: string
    metrics: {
        bloodPressure: string
        heartRate: string
        bloodGlucose: string
        temperature: string
        oxygenSaturation: string
        weight: string
    }
}

const exportUiText: Record<DashboardLanguage, ExportUiText> = {
    vi: {
        formatAriaLabel: "Định dạng xuất dữ liệu",
        filterAriaLabel: "Bộ lọc hồ sơ",
        exportTextButton: "Xuất hồ sơ tổng",
        exportFilesButton: "Xuất tệp y khoa",
        importTextButton: "Nhập hồ sơ tổng",
        exporting: "Đang xuất...",
        importing: "Đang nhập...",
        exportHint: "Xuất hồ sơ tổng ra tệp ZIP gồm dữ liệu văn bản và tệp y khoa.",
        missingPatientDataId: "Không thể xuất dữ liệu: thiếu mã bệnh nhân.",
        missingPatientFilesId: "Không thể xuất tệp: thiếu mã bệnh nhân.",
        missingPatientImportId: "Không thể nhập dữ liệu: thiếu mã bệnh nhân.",
        invalidImportFileType: "Tệp nhập không hợp lệ. Nhập hồ sơ tổng chỉ hỗ trợ .zip.",
        exportTextSuccessJson: "Đã xuất hồ sơ tổng ZIP (văn bản JSON).",
        exportTextSuccessPdf: "Đã xuất hồ sơ tổng ZIP (văn bản PDF).",
        exportFilesSuccess: "Đã xuất tệp đính kèm dạng ZIP.",
        importSuccess: "Đã nhập dữ liệu bệnh nhân.",
        exportTextFailed: "Xuất dữ liệu bệnh nhân thất bại.",
        exportFilesFailed: "Xuất tệp đính kèm thất bại.",
        importFailed: "Nhập dữ liệu bệnh nhân thất bại.",
    },
    en: {
        formatAriaLabel: "Data export format",
        filterAriaLabel: "Record filter",
        exportTextButton: "Export full record",
        exportFilesButton: "Export medical files",
        importTextButton: "Import full record",
        exporting: "Exporting...",
        importing: "Importing...",
        exportHint: "Full export downloads one ZIP with text data and original medical files.",
        missingPatientDataId: "Cannot export data: missing patient id.",
        missingPatientFilesId: "Cannot export files: missing patient id.",
        missingPatientImportId: "Cannot import data: missing patient id.",
        invalidImportFileType: "Invalid import file. Global import supports .zip only.",
        exportTextSuccessJson: "Full patient record exported as ZIP (JSON text).",
        exportTextSuccessPdf: "Full patient record exported as ZIP (PDF text).",
        exportFilesSuccess: "Patient attachments exported as ZIP.",
        importSuccess: "Patient data imported.",
        exportTextFailed: "Failed to export patient data.",
        exportFilesFailed: "Failed to export patient files.",
        importFailed: "Failed to import patient data.",
    },
}

const patientDetailUiText: Record<DashboardLanguage, PatientDetailUiText> = {
    vi: {
        locale: "vi-VN",
        backButton: "Quay lại",
        pageTitle: "Hồ sơ bệnh nhân",
        loadingPatient: "Đang tải hồ sơ bệnh nhân...",
        loadPatientErrorTitle: "Không thể tải hồ sơ bệnh nhân",
        loadPatientErrorHint: "Vui lòng thử lại sau",
        photoCardTitle: "Ảnh hồ sơ",
        patientPhotoUploadLabel: "Tải ảnh mới",
        photoUploadFailed: "Tải ảnh thất bại. Vui lòng thử lại.",
        photoUpdateSuccess: "Đã cập nhật ảnh hồ sơ.",
        photoUploadButton: "Cập nhật ảnh",
        uploadingLabel: "Đang tải...",
        savingLabel: "Đang lưu...",
        updatingLabel: "Đang cập nhật...",
        deletingLabel: "Đang xóa...",
        vitalsCardTitle: "Chỉ số sinh tồn",
        vitalRecordedAtLabel: "Thời gian đo",
        vitalSourceLabel: "Nguồn dữ liệu",
        vitalBpSystolicLabel: "Huyết áp tâm thu",
        vitalBpDiastolicLabel: "Huyết áp tâm trương",
        vitalHeartRateLabel: "Nhịp tim (bpm)",
        vitalSpo2Label: "SpO₂ (%)",
        vitalTemperatureLabel: "Nhiệt độ (°C)",
        vitalWeightLabel: "Cân nặng (kg)",
        vitalBloodGlucoseLabel: "Đường huyết (mmol/L)",
        vitalGlucoseTimingLabel: "Thời điểm đo",
        vitalNotesLabel: "Ghi chú",
        vitalNotesPlaceholder: "Nhập ghi chú nếu cần",
        vitalSaveFailed: "Lưu chỉ số thất bại. Vui lòng thử lại.",
        vitalSaveButton: "Lưu chỉ số",
        vitalSaveSuccess: "Đã lưu chỉ số sinh tồn.",
        recentHistoryLabel: "Lịch sử gần đây",
        recordCountSuffix: "bản ghi",
        vitalsLoading: "Đang tải dữ liệu sinh tồn...",
        vitalsLoadFailed: "Không thể tải dữ liệu sinh tồn.",
        vitalsEmpty: "Chưa có chỉ số sinh tồn nào.",
        medicalRecordsTitle: "Hồ sơ y khoa",
        medicalRecordsSubtitle: "Xem và lọc các tài liệu đã tải lên",
        recordsLoading: "Đang tải hồ sơ y khoa...",
        recordsLoadFailed: "Không thể tải hồ sơ y khoa.",
        recordsEmpty: "Chưa có hồ sơ y khoa nào.",
        recordVerifiedBadge: "Đã xác thực",
        editButton: "Chỉnh sửa",
        deleteButton: "Xóa",
        downloadPdf: "Tải PDF",
        noAttachment: "Không có tệp đính kèm",
        imagingCardTitle: "Ảnh cận lâm sàng",
        imagingTypeLabel: "Loại ảnh",
        recordTitleLabel: "Tiêu đề (tùy chọn)",
        recordTitlePlaceholder: "Ví dụ: CT ngực 2026-02-01",
        recordFileLabel: "Tải ảnh cận lâm sàng",
        recordUploadFailed: "Tải ảnh thất bại. Vui lòng thử lại.",
        recordUploadButton: "Tải ảnh cận lâm sàng",
        postUploadDialogTitle: "Thêm nhận xét bác sĩ (tùy chọn)",
        postUploadDialogHint: "AI đã phân tích xong. Bạn có thể bổ sung nhận xét bác sĩ cho hồ sơ này.",
        postUploadNoAnalysis: "Chưa có nội dung phân tích AI để tham khảo.",
        doctorCommentPlaceholder: "Nhập nhận xét bác sĩ...",
        skipButton: "Bỏ qua",
        saveCommentButton: "Lưu nhận xét",
        editDialogTitle: "Cập nhật hồ sơ y khoa",
        editRecordTitleLabel: "Tiêu đề",
        editRecordTypeLabel: "Loại hồ sơ",
        editRecordFileLabel: "Thay tệp (tùy chọn)",
        editRecordFileHint: "Nếu thay tệp, hệ thống sẽ chạy lại phân tích AI.",
        editRecordCommentLabel: "Nhận xét bác sĩ",
        cancelButton: "Hủy",
        saveChangesButton: "Lưu thay đổi",
        deleteDialogTitle: "Xóa hồ sơ y khoa?",
        deleteDialogDescription: "Tệp, kết quả phân tích AI và dữ liệu liên quan của bản ghi này sẽ bị xóa.",
        activeRecordFallbackTitle: "Ảnh cận lâm sàng",
        activeRecordNoImage: "Không có ảnh hiển thị",
        uploadProgressTitle: "Đang xử lý tải ảnh cận lâm sàng",
        uploadCompleted: "Hoàn tất. Đang cập nhật dữ liệu...",
        uploadFailed: "Tải lên thất bại.",
        uploadStageUpload: "Đang tải tệp lên máy chủ...",
        uploadStageValidate: "Đang xác thực và lưu tệp...",
        uploadStageEcgEmbedding: "Đang tạo ECG embedding (MedSigLIP)...",
        uploadStageEcgClassifier: "Đang chạy ECG classifier...",
        uploadStageImageAnalysis: "Đang phân tích hình ảnh...",
        uploadStageAiAnalysis: "Đang phân tích AI bằng MedGemma...",
        uploadStageSave: "Đang lưu kết quả vào hồ sơ...",
        errors: {
            missingPatientId: "Không tìm thấy mã bệnh nhân.",
            choosePhotoFirst: "Vui lòng chọn ảnh trước khi tải lên.",
            invalidPhotoFile: "Tệp không hợp lệ. Vui lòng chọn ảnh.",
            chooseImagingFileFirst: "Vui lòng chọn ảnh cận lâm sàng.",
            invalidImagingFile: "Tệp không hợp lệ. Vui lòng chọn ảnh.",
            recordUploadFallback: "Tải ảnh thất bại. Vui lòng thử lại.",
            saveDoctorCommentFailed: "Không thể lưu nhận xét bác sĩ.",
            replacementFileInvalid: "Tệp thay thế phải là ảnh hoặc PDF.",
            updateRecordFailed: "Cập nhật hồ sơ y khoa thất bại.",
            deleteRecordFailed: "Xóa hồ sơ y khoa thất bại.",
            enterAtLeastOneVital: "Vui lòng nhập ít nhất một chỉ số.",
        },
        success: {
            recordUploadSuccess: "Đã tải tệp thành công.",
            saveDoctorCommentSuccess: "Đã lưu nhận xét bác sĩ.",
            updateRecordSuccess: "Đã cập nhật hồ sơ y khoa.",
            deleteRecordSuccess: "Đã xóa hồ sơ y khoa thành công.",
        },
        options: {
            imagingType: {
                lab: "Xét nghiệm",
                xray: "X-quang",
                ecg: "Điện tâm đồ (ECG)",
                ct: "CT",
                mri: "MRI",
            },
            recordType: {
                "": "Tất cả",
                prescription: "Đơn thuốc",
                lab: "Xét nghiệm",
                xray: "X-quang",
                ecg: "ECG",
                ct: "CT",
                mri: "MRI",
                notes: "Ghi chú",
                referral: "Chuyển tuyến",
            },
            vitalSource: {
                self_reported: "Tự báo cáo",
                clinic: "Phòng khám",
                hospital: "Bệnh viện",
                device: "Thiết bị",
                unknown: "Không rõ",
            },
            glucoseTiming: {
                "": "Không rõ",
                fasting: "Lúc đói",
                before_meal: "Trước ăn",
                after_meal: "Sau ăn",
                random: "Ngẫu nhiên",
            },
        },
        summaryCardTitle: "Tóm tắt lâm sàng",
        summaryCardSubtitle: "Tóm tắt hồ sơ y khoa bằng AI",
        summaryGenerateButton: "Tạo tóm tắt",
        summaryRegenerateButton: "Tạo lại",
        summaryGenerating: "Đang tạo tóm tắt...",
        summaryGeneratingHint: "MedGemma đang phân tích dữ liệu bệnh nhân...",
        summaryError: "Không thể tạo tóm tắt. Vui lòng thử lại.",
        summaryTimestamp: "Tạo lúc",
        summaryModel: "Mô hình",
        metrics: {
            bloodPressure: "HA",
            heartRate: "Mạch",
            bloodGlucose: "Đường huyết",
            temperature: "Nhiệt độ",
            oxygenSaturation: "SpO2",
            weight: "Cân nặng",
        },
    },
    en: {
        locale: "en-US",
        backButton: "Back",
        pageTitle: "Patient Profile",
        loadingPatient: "Loading patient profile...",
        loadPatientErrorTitle: "Unable to load patient profile",
        loadPatientErrorHint: "Please try again later",
        photoCardTitle: "Profile Photo",
        patientPhotoUploadLabel: "Upload new photo",
        photoUploadFailed: "Photo upload failed. Please try again.",
        photoUpdateSuccess: "Profile photo updated.",
        photoUploadButton: "Update photo",
        uploadingLabel: "Uploading...",
        savingLabel: "Saving...",
        updatingLabel: "Updating...",
        deletingLabel: "Deleting...",
        vitalsCardTitle: "Vital Signs",
        vitalRecordedAtLabel: "Recorded at",
        vitalSourceLabel: "Data source",
        vitalBpSystolicLabel: "Systolic blood pressure",
        vitalBpDiastolicLabel: "Diastolic blood pressure",
        vitalHeartRateLabel: "Heart rate (bpm)",
        vitalSpo2Label: "SpO2 (%)",
        vitalTemperatureLabel: "Temperature (°C)",
        vitalWeightLabel: "Weight (kg)",
        vitalBloodGlucoseLabel: "Blood glucose (mmol/L)",
        vitalGlucoseTimingLabel: "Measurement timing",
        vitalNotesLabel: "Notes",
        vitalNotesPlaceholder: "Add notes if needed",
        vitalSaveFailed: "Saving vital signs failed. Please try again.",
        vitalSaveButton: "Save vitals",
        vitalSaveSuccess: "Vital signs saved.",
        recentHistoryLabel: "Recent history",
        recordCountSuffix: "records",
        vitalsLoading: "Loading vital data...",
        vitalsLoadFailed: "Unable to load vital data.",
        vitalsEmpty: "No vital records yet.",
        medicalRecordsTitle: "Medical Records",
        medicalRecordsSubtitle: "View and filter uploaded documents",
        recordsLoading: "Loading medical records...",
        recordsLoadFailed: "Unable to load medical records.",
        recordsEmpty: "No medical records yet.",
        recordVerifiedBadge: "Verified",
        editButton: "Edit",
        deleteButton: "Delete",
        downloadPdf: "Download PDF",
        noAttachment: "No attachment",
        imagingCardTitle: "Clinical Images",
        imagingTypeLabel: "Image type",
        recordTitleLabel: "Title (optional)",
        recordTitlePlaceholder: "Example: Chest CT 2026-02-01",
        recordFileLabel: "Upload clinical image",
        recordUploadFailed: "Image upload failed. Please try again.",
        recordUploadButton: "Upload clinical image",
        postUploadDialogTitle: "Add doctor comment (optional)",
        postUploadDialogHint: "AI analysis is complete. You can add doctor comments for this record.",
        postUploadNoAnalysis: "No AI analysis available for reference yet.",
        doctorCommentPlaceholder: "Enter doctor comment...",
        skipButton: "Skip",
        saveCommentButton: "Save comment",
        editDialogTitle: "Update medical record",
        editRecordTitleLabel: "Title",
        editRecordTypeLabel: "Record type",
        editRecordFileLabel: "Replace file (optional)",
        editRecordFileHint: "Replacing the file will trigger AI analysis again.",
        editRecordCommentLabel: "Doctor comment",
        cancelButton: "Cancel",
        saveChangesButton: "Save changes",
        deleteDialogTitle: "Delete medical record?",
        deleteDialogDescription: "The file, AI analysis result, and related data of this record will be deleted.",
        activeRecordFallbackTitle: "Clinical image",
        activeRecordNoImage: "No image available",
        uploadProgressTitle: "Processing clinical image upload",
        uploadCompleted: "Completed. Updating data...",
        uploadFailed: "Upload failed.",
        uploadStageUpload: "Uploading file to server...",
        uploadStageValidate: "Validating and saving file...",
        uploadStageEcgEmbedding: "Generating ECG embedding (MedSigLIP)...",
        uploadStageEcgClassifier: "Running ECG classifier...",
        uploadStageImageAnalysis: "Analyzing image...",
        uploadStageAiAnalysis: "Running AI analysis with MedGemma...",
        uploadStageSave: "Saving result to record...",
        errors: {
            missingPatientId: "Patient id not found.",
            choosePhotoFirst: "Please choose a photo before uploading.",
            invalidPhotoFile: "Invalid file. Please choose an image.",
            chooseImagingFileFirst: "Please choose a clinical image.",
            invalidImagingFile: "Invalid file. Please choose an image.",
            recordUploadFallback: "Image upload failed. Please try again.",
            saveDoctorCommentFailed: "Unable to save doctor comment.",
            replacementFileInvalid: "Replacement file must be an image or PDF.",
            updateRecordFailed: "Failed to update medical record.",
            deleteRecordFailed: "Failed to delete medical record.",
            enterAtLeastOneVital: "Please enter at least one measurement.",
        },
        success: {
            recordUploadSuccess: "File uploaded successfully.",
            saveDoctorCommentSuccess: "Doctor comment saved.",
            updateRecordSuccess: "Medical record updated.",
            deleteRecordSuccess: "Medical record deleted successfully.",
        },
        options: {
            imagingType: {
                lab: "Lab result",
                xray: "X-ray",
                ecg: "Electrocardiogram (ECG)",
                ct: "CT",
                mri: "MRI",
            },
            recordType: {
                "": "All",
                prescription: "Prescription",
                lab: "Lab result",
                xray: "X-ray",
                ecg: "ECG",
                ct: "CT",
                mri: "MRI",
                notes: "Notes",
                referral: "Referral",
            },
            vitalSource: {
                self_reported: "Self reported",
                clinic: "Clinic",
                hospital: "Hospital",
                device: "Thiet bi",
                unknown: "Unknown",
            },
            glucoseTiming: {
                "": "Unknown",
                fasting: "Fasting",
                before_meal: "Before meal",
                after_meal: "After meal",
                random: "Random",
            },
        },
        summaryCardTitle: "Clinical Summary",
        summaryCardSubtitle: "AI-generated medical profile summary",
        summaryGenerateButton: "Generate Summary",
        summaryRegenerateButton: "Regenerate",
        summaryGenerating: "Generating summary...",
        summaryGeneratingHint: "MedGemma is analyzing patient data...",
        summaryError: "Unable to generate summary. Please try again.",
        summaryTimestamp: "Generated at",
        summaryModel: "Model",
        metrics: {
            bloodPressure: "BP",
            heartRate: "Heart rate",
            bloodGlucose: "Blood glucose",
            temperature: "Nhiet do",
            oxygenSaturation: "SpO2",
            weight: "Weight",
        },
    },
}

type VitalFormState = {
    recordedAt: string
    source: string
    bloodPressureSystolic: string
    bloodPressureDiastolic: string
    heartRate: string
    bloodGlucose: string
    bloodGlucoseTiming: string
    temperature: string
    oxygenSaturation: string
    weightKg: string
    reasonForVisit: string
    testResultComment: string
    patientProgress: string
    treatmentPlan: string
    doctorNotes: string
    notes: string
}

type RecordEditState = {
    recordId: string
    title: string
    recordType:
    | "prescription"
    | "lab"
    | "xray"
    | "ecg"
    | "ct"
    | "mri"
    | "notes"
    | "referral"
    doctorComment: string
    file: File | null
}

const TEST_RESULT_RECORD_TYPES = new Set(["lab", "xray", "ecg", "ct", "mri"])

const MEDICAL_HISTORY_KEYS: MedicalHistoryFieldKey[] = [
    "chronic_conditions",
    "past_surgeries",
    "hospitalizations",
    "medications_history",
    "allergies",
    "psychiatric_history",
    "family_history_of_chronic_conditions",
    "family_history_of_mental_health_conditions",
    "family_history_of_genetic_conditions",
    "vaccines_administered",
    "vaccines_due",
    "previous_treatments",
    "physiotherapy",
    "other_relevant_treatments",
]

const MEDICAL_HISTORY_FIELD_GROUPS: MedicalHistoryFieldGroup[] = [
    {
        title: {
            vi: "Tiền sử bệnh lý",
            en: "Medical History",
        },
        fields: [
            {
                key: "chronic_conditions",
                label: { vi: "Bệnh mạn tính", en: "Chronic Conditions" },
                placeholder: { vi: "Nhập 1 tình trạng mỗi dòng", en: "Enter one condition per line" },
            },
            {
                key: "past_surgeries",
                label: { vi: "Phẫu thuật trước đây", en: "Past Surgeries" },
                placeholder: { vi: "Nhập 1 phẫu thuật mỗi dòng", en: "Enter one surgery per line" },
            },
            {
                key: "hospitalizations",
                label: { vi: "Nhập viện", en: "Hospitalizations" },
                placeholder: { vi: "Nhập 1 lần nhập viện mỗi dòng", en: "Enter one hospitalization per line" },
            },
            {
                key: "medications_history",
                label: { vi: "Tiền sử dùng thuốc", en: "Medications History" },
                placeholder: { vi: "Nhập 1 thuốc mỗi dòng", en: "Enter one medication history item per line" },
            },
            {
                key: "allergies",
                label: { vi: "Dị ứng", en: "Allergies" },
                placeholder: { vi: "Nhập 1 dị ứng mỗi dòng", en: "Enter one allergy per line" },
            },
            {
                key: "psychiatric_history",
                label: { vi: "Tiền sử tâm thần", en: "Psychiatric History" },
                placeholder: { vi: "Nhập 1 mục mỗi dòng", en: "Enter one psychiatric history item per line" },
            },
        ],
    },
    {
        title: {
            vi: "Tiền sử gia đình",
            en: "Family Medical History",
        },
        fields: [
            {
                key: "family_history_of_chronic_conditions",
                label: { vi: "Gia đình có bệnh mạn tính", en: "Family History of Chronic Conditions" },
                placeholder: { vi: "Nhập 1 mục mỗi dòng", en: "Enter one family chronic condition per line" },
            },
            {
                key: "family_history_of_mental_health_conditions",
                label: { vi: "Gia đình có bệnh tâm thần", en: "Family History of Mental Health Conditions" },
                placeholder: { vi: "Nhập 1 mục mỗi dòng", en: "Enter one family mental health condition per line" },
            },
            {
                key: "family_history_of_genetic_conditions",
                label: { vi: "Gia đình có bệnh di truyền", en: "Family History of Genetic Conditions" },
                placeholder: { vi: "Nhập 1 mục mỗi dòng", en: "Enter one family genetic condition per line" },
            },
        ],
    },
    {
        title: {
            vi: "Tiêm chủng",
            en: "Immunization Records",
        },
        fields: [
            {
                key: "vaccines_administered",
                label: { vi: "Vaccine đã tiêm", en: "Vaccines Administered" },
                placeholder: { vi: "Nhập 1 vaccine mỗi dòng", en: "Enter one administered vaccine per line" },
            },
            {
                key: "vaccines_due",
                label: { vi: "Vaccine đến hạn", en: "Vaccines Due" },
                placeholder: { vi: "Nhập 1 vaccine mỗi dòng", en: "Enter one due vaccine per line" },
            },
        ],
    },
    {
        title: {
            vi: "Tiền sử điều trị",
            en: "Treatment History",
        },
        fields: [
            {
                key: "previous_treatments",
                label: { vi: "Điều trị trước đây", en: "Previous Treatments" },
                placeholder: { vi: "Nhập 1 điều trị mỗi dòng", en: "Enter one previous treatment per line" },
            },
            {
                key: "physiotherapy",
                label: { vi: "Vật lý trị liệu", en: "Physiotherapy" },
                placeholder: { vi: "Nhập 1 mục mỗi dòng", en: "Enter one physiotherapy item per line" },
            },
            {
                key: "other_relevant_treatments",
                label: { vi: "Điều trị liên quan khác", en: "Other Relevant Treatments" },
                placeholder: { vi: "Nhập 1 điều trị mỗi dòng", en: "Enter one treatment item per line" },
            },
        ],
    },
]

function getRecordUploadStage(
    progress: number,
    recordType: ImagingRecordType,
    uiText: PatientDetailUiText
): string {
    if (progress < 18) return uiText.uploadStageUpload
    if (progress < 34) return uiText.uploadStageValidate

    if (recordType === "ecg") {
        if (progress < 52) return uiText.uploadStageEcgEmbedding
        if (progress < 68) return uiText.uploadStageEcgClassifier
    } else {
        if (progress < 68) return uiText.uploadStageImageAnalysis
    }

    if (progress < 88) return uiText.uploadStageAiAnalysis
    return uiText.uploadStageSave
}

function nextRecordUploadProgress(current: number): number {
    if (current < 20) return Math.min(97, current + 4.0)
    if (current < 40) return Math.min(97, current + 2.6)
    if (current < 60) return Math.min(97, current + 1.8)
    if (current < 80) return Math.min(97, current + 1.0)
    if (current < 92) return Math.min(97, current + 0.6)
    return Math.min(97, current + 0.25)
}

export default function PatientDetailPage() {
    const router = useRouter()
    const { role, user } = useAuth()
    const { language } = useDashboardLanguage()
    const params = useParams()
    const patientId = Array.isArray(params.patientId) ? params.patientId[0] : params.patientId
    const exportText = exportUiText[language]
    const uiText = patientDetailUiText[language]
    const imagingTypeOptions = useMemo(
        () => (["lab", "xray", "ecg", "ct", "mri"] as const).map((value) => ({ value, label: uiText.options.imagingType[value] })),
        [uiText]
    )
    const recordTypeOptions = useMemo(
        () =>
            (["", "lab", "xray", "ecg", "ct", "mri"] as const).map((value) => ({
                value,
                label: uiText.options.recordType[value],
            })),
        [uiText]
    )
    const vitalSourceOptions = useMemo(
        () =>
            (["self_reported", "clinic", "hospital", "device"] as const).map((value) => ({
                value,
                label: uiText.options.vitalSource[value],
            })),
        [uiText]
    )
    const glucoseTimingOptions = useMemo(
        () =>
            (["", "fasting", "before_meal", "after_meal", "random"] as const).map((value) => ({
                value,
                label: uiText.options.glucoseTiming[value],
            })),
        [uiText]
    )
    const recordTypeLabels = uiText.options.recordType

    const [recordFilter, setRecordFilter] = useState("")
    const [textExportFormat, setTextExportFormat] = useState<TextExportFormat>("json")
    const [vitalExportFormat, setVitalExportFormat] = useState<TextExportFormat>("json")
    const [medicalHistoryExportFormat, setMedicalHistoryExportFormat] = useState<TextExportFormat>("json")
    const [activeRecord, setActiveRecord] = useState<MedicalRecord | null>(null)

    const { data, isLoading, error } = usePatient(patientId ?? "")
    const {
        data: recordsData,
        isLoading: recordsLoading,
        error: recordsError,
        refetch: refetchRecords,
    } = usePatientRecords(patientId ?? "", recordFilter || undefined, 50)
    const { data: vitalsData, isLoading: vitalsLoading, error: vitalsError } = usePatientVitals(
        patientId ?? "",
        30
    )
    const photoUploadMutation = useUploadPatientPhoto()
    const recordUploadMutation = useUploadPatientRecordImage()
    const recordUpdateMutation = useUpdatePatientRecord()
    const recordDeleteMutation = useDeletePatientRecord()
    const exportPatientTextMutation = useExportPatientText()
    const exportVitalSignsMutation = useExportVitalSigns()
    const exportMedicalHistoryMutation = useExportMedicalHistory()
    const importVitalPreviewMutation = useImportVitalSignsPreview()
    const importMedicalHistoryPreviewMutation = useImportMedicalHistoryPreview()
    const importPatientTextMutation = useImportPatientText()
    const createVitalMutation = useCreateVitalSign()
    const updateVitalMutation = useUpdateVitalSign()
    const deleteVitalMutation = useDeleteVitalSign()
    const updatePatientMutation = useUpdatePatient()

    const [photoFile, setPhotoFile] = useState<File | null>(null)
    const [photoError, setPhotoError] = useState<string | null>(null)
    const photoInputRef = useRef<HTMLInputElement>(null)
    const importInputRef = useRef<HTMLInputElement>(null)
    const vitalImportInputRef = useRef<HTMLInputElement>(null)
    const medicalHistoryImportInputRef = useRef<HTMLInputElement>(null)
    const [isImportProgressOpen, setIsImportProgressOpen] = useState(false)
    const [importProgressValue, setImportProgressValue] = useState(0)
    const [importProgressStage, setImportProgressStage] = useState("")

    const [recordFile, setRecordFile] = useState<File | null>(null)
    const [recordType, setRecordType] = useState<ImagingRecordType>("xray")
    const [recordTitle, setRecordTitle] = useState("")
    const [recordError, setRecordError] = useState<string | null>(null)
    const recordInputRef = useRef<HTMLInputElement>(null)
    const [isRecordUploadDialogOpen, setIsRecordUploadDialogOpen] = useState(false)
    const [selectedCheckupForUploadId, setSelectedCheckupForUploadId] = useState<string | null>(null)
    const [postUploadLinkedCheckupId, setPostUploadLinkedCheckupId] = useState<string | null>(null)
    const [postUploadRecordId, setPostUploadRecordId] = useState<string | null>(null)
    const [postUploadTestResultDescription, setPostUploadTestResultDescription] = useState("")
    const [postUploadFinalConclusion, setPostUploadFinalConclusion] = useState("")
    const [postUploadComment, setPostUploadComment] = useState("")
    const [postUploadAiAnalysis, setPostUploadAiAnalysis] = useState<MedicalRecordAIAnalysis | string | null>(null)
    const [isPostUploadDialogOpen, setIsPostUploadDialogOpen] = useState(false)
    const [isUploadProgressOpen, setIsUploadProgressOpen] = useState(false)
    const [uploadProgressValue, setUploadProgressValue] = useState(0)
    const [uploadProgressStage, setUploadProgressStage] = useState("")
    const [uploadProgressType, setUploadProgressType] = useState<ImagingRecordType>("xray")
    const uploadProgressTimerRef = useRef<number | null>(null)
    const uploadProgressHideTimeoutRef = useRef<number | null>(null)

    const [editState, setEditState] = useState<RecordEditState | null>(null)
    const [editError, setEditError] = useState<string | null>(null)
    const [deleteRecord, setDeleteRecord] = useState<MedicalRecord | null>(null)
    const [recordListError, setRecordListError] = useState<string | null>(null)

    const summaryMutation = useGeneratePatientSummary()
    const [summaryText, setSummaryText] = useState<string | null>(null)
    const [summaryMeta, setSummaryMeta] = useState<{ generated_at: string; model: string } | null>(null)
    const formattedSummaryText = useMemo(
        () => normalizeClinicalSummaryMarkdown(summaryText),
        [summaryText]
    )

    const [vitalForm, setVitalForm] = useState<VitalFormState>({
        recordedAt: "",
        source: role === "doctor" ? "clinic" : "self_reported",
        bloodPressureSystolic: "",
        bloodPressureDiastolic: "",
        heartRate: "",
        bloodGlucose: "",
        bloodGlucoseTiming: "",
        temperature: "",
        oxygenSaturation: "",
        weightKg: "",
        reasonForVisit: "",
        testResultComment: "",
        patientProgress: "",
        treatmentPlan: "",
        doctorNotes: "",
        notes: "",
    })
    const [vitalError, setVitalError] = useState<string | null>(null)
    const [vitalSuccess, setVitalSuccess] = useState<string | null>(null)
    const [editingVitalId, setEditingVitalId] = useState<string | null>(null)
    const [isCheckupFormVisible, setIsCheckupFormVisible] = useState(false)
    const [deleteVital, setDeleteVital] = useState<VitalSign | null>(null)
    const [isMedicalHistoryEditing, setIsMedicalHistoryEditing] = useState(false)
    const [medicalHistoryForm, setMedicalHistoryForm] = useState<MedicalHistoryFormState>(
        () => createEmptyMedicalHistoryFormState()
    )
    const [medicalHistoryError, setMedicalHistoryError] = useState<string | null>(null)
    const [medicalHistorySuccess, setMedicalHistorySuccess] = useState<string | null>(null)

    const clearUploadProgressTimer = () => {
        if (uploadProgressTimerRef.current !== null) {
            window.clearInterval(uploadProgressTimerRef.current)
            uploadProgressTimerRef.current = null
        }
    }

    const clearUploadProgressHideTimeout = () => {
        if (uploadProgressHideTimeoutRef.current !== null) {
            window.clearTimeout(uploadProgressHideTimeoutRef.current)
            uploadProgressHideTimeoutRef.current = null
        }
    }

    const startUploadProgress = (recordTypeForUpload: ImagingRecordType) => {
        clearUploadProgressTimer()
        clearUploadProgressHideTimeout()
        setUploadProgressType(recordTypeForUpload)
        setUploadProgressValue(4)
        setUploadProgressStage("")
        setIsUploadProgressOpen(true)

        uploadProgressTimerRef.current = window.setInterval(() => {
            setUploadProgressValue((prev) => nextRecordUploadProgress(prev))
        }, 450)
    }

    const finishUploadProgress = (status: "success" | "error") => {
        clearUploadProgressTimer()

        if (status === "success") {
            setUploadProgressValue(100)
            setUploadProgressStage(uiText.uploadCompleted)
            clearUploadProgressHideTimeout()
            uploadProgressHideTimeoutRef.current = window.setTimeout(() => {
                setIsUploadProgressOpen(false)
                setUploadProgressValue(0)
                setUploadProgressStage("")
            }, 800)
            return
        }

        setUploadProgressStage(uiText.uploadFailed)
        clearUploadProgressHideTimeout()
        uploadProgressHideTimeoutRef.current = window.setTimeout(() => {
            setIsUploadProgressOpen(false)
            setUploadProgressValue(0)
            setUploadProgressStage("")
        }, 1200)
    }

    useEffect(() => {
        return () => {
            clearUploadProgressTimer()
            clearUploadProgressHideTimeout()
        }
    }, [])

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] ?? null
        setPhotoFile(selected)
        setPhotoError(null)
    }

    const handleUpload = () => {
        if (!patientId) {
            setPhotoError(uiText.errors.missingPatientId)
            return
        }
        if (!photoFile) {
            setPhotoError(uiText.errors.choosePhotoFirst)
            return
        }
        if (!photoFile.type.startsWith("image/")) {
            setPhotoError(uiText.errors.invalidPhotoFile)
            return
        }

        photoUploadMutation.mutate(
            { patientId, file: photoFile },
            {
                onSuccess: () => {
                    setPhotoFile(null)
                    if (photoInputRef.current) {
                        photoInputRef.current.value = ""
                    }
                },
            }
        )
    }

    const handleRecordFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] ?? null
        setRecordFile(selected)
        setRecordError(null)
        setRecordListError(null)
    }

    const resetRecordUploadForm = () => {
        setRecordFile(null)
        setRecordTitle("")
        setRecordError(null)
        recordUploadMutation.reset()
        if (recordInputRef.current) {
            recordInputRef.current.value = ""
        }
    }

    const handleRecordUploadDialogOpenChange = (open: boolean) => {
        if (!open && recordUploadMutation.isPending) {
            return
        }
        setIsRecordUploadDialogOpen(open)
        if (!open) {
            resetRecordUploadForm()
            setSelectedCheckupForUploadId(null)
        }
    }

    const openRecordUploadDialog = (checkupId?: string) => {
        setRecordError(null)
        setRecordListError(null)
        setSelectedCheckupForUploadId(checkupId ?? null)
        setIsRecordUploadDialogOpen(true)
    }

    const handleRecordUpload = () => {
        setRecordError(null)
        setRecordListError(null)
        if (!patientId) {
            setRecordError(uiText.errors.missingPatientId)
            return
        }
        if (!recordFile) {
            setRecordError(uiText.errors.chooseImagingFileFirst)
            return
        }
        if (!recordFile.type.startsWith("image/")) {
            setRecordError(uiText.errors.invalidImagingFile)
            return
        }

        startUploadProgress(recordType)
        const linkedCheckupId = selectedCheckupForUploadId

        recordUploadMutation.mutate(
            {
                patientId,
                recordType,
                file: recordFile,
                title: recordTitle.trim() || undefined,
                doctorComment: buildDoctorRecordComment(
                    {
                        testResultDescription: "",
                        finalConclusion: "",
                        additionalNotes: "",
                    },
                    linkedCheckupId || undefined
                ),
            },
            {
                onSuccess: (response) => {
                    finishUploadProgress("success")
                    resetRecordUploadForm()
                    setIsRecordUploadDialogOpen(false)
                    setSelectedCheckupForUploadId(null)
                    toast.success(uiText.success.recordUploadSuccess)
                    setPostUploadRecordId(response.record_id)
                    setPostUploadLinkedCheckupId(linkedCheckupId)
                    setPostUploadTestResultDescription("")
                    setPostUploadFinalConclusion("")
                    setPostUploadComment("")
                    setPostUploadAiAnalysis(response.ai_analysis ?? null)
                    setIsPostUploadDialogOpen(true)
                    void refetchRecords()
                },
                onError: (err) => {
                    finishUploadProgress("error")
                    setRecordError(getErrorMessage(err, uiText.errors.recordUploadFallback))
                },
            }
        )
    }

    const handlePostUploadCommentSave = () => {
        if (!patientId || !postUploadRecordId) {
            setIsPostUploadDialogOpen(false)
            setPostUploadLinkedCheckupId(null)
            return
        }

        recordUpdateMutation.mutate(
            {
                patientId,
                recordId: postUploadRecordId,
                doctorComment: buildDoctorRecordComment(
                    {
                        testResultDescription: postUploadTestResultDescription,
                        finalConclusion: postUploadFinalConclusion,
                        additionalNotes: postUploadComment,
                    },
                    postUploadLinkedCheckupId || undefined
                ),
            },
            {
                onSuccess: () => {
                    setIsPostUploadDialogOpen(false)
                    setPostUploadRecordId(null)
                    setPostUploadLinkedCheckupId(null)
                    setPostUploadTestResultDescription("")
                    setPostUploadFinalConclusion("")
                    setPostUploadComment("")
                    setPostUploadAiAnalysis(null)
                    toast.success(uiText.success.saveDoctorCommentSuccess)
                    void refetchRecords()
                },
                onError: (err) => {
                    setRecordError(getErrorMessage(err, uiText.errors.saveDoctorCommentFailed))
                },
            }
        )
    }

    const openEditRecord = (record: MedicalRecord) => {
        setEditError(null)
        setRecordListError(null)
        setEditState({
            recordId: record.id,
            title: record.title || "",
            recordType: record.record_type,
            doctorComment: record.doctor_comment || "",
            file: null,
        })
    }

    const handleEditRecordFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const selected = event.target.files?.[0] ?? null
        setEditState((prev) => {
            if (!prev) return prev
            return {
                ...prev,
                file: selected,
            }
        })
    }

    const handleRecordUpdate = () => {
        if (!patientId || !editState) {
            return
        }

        setEditError(null)
        setRecordListError(null)

        if (editState.file && !editState.file.type.startsWith("image/") && editState.file.type !== "application/pdf") {
            setEditError(uiText.errors.replacementFileInvalid)
            return
        }

        recordUpdateMutation.mutate(
            {
                patientId,
                recordId: editState.recordId,
                title: editState.title,
                recordType: editState.recordType,
                doctorComment: editState.doctorComment,
                file: editState.file ?? undefined,
            },
            {
                onSuccess: () => {
                    setEditState(null)
                    setEditError(null)
                    toast.success(uiText.success.updateRecordSuccess)
                    if (activeRecord?.id === editState.recordId) {
                        setActiveRecord(null)
                    }
                    void refetchRecords()
                },
                onError: (err) => {
                    setEditError(getErrorMessage(err, uiText.errors.updateRecordFailed))
                },
            }
        )
    }

    const handleDeleteRecord = () => {
        if (!patientId || !deleteRecord) {
            return
        }

        setRecordListError(null)

        recordDeleteMutation.mutate(
            {
                patientId,
                recordId: deleteRecord.id,
            },
            {
                onSuccess: () => {
                    if (activeRecord?.id === deleteRecord.id) {
                        setActiveRecord(null)
                    }
                    setDeleteRecord(null)
                    toast.success(uiText.success.deleteRecordSuccess)
                    void refetchRecords()
                },
                onError: (err) => {
                    setRecordListError(getErrorMessage(err, uiText.errors.deleteRecordFailed))
                },
            }
        )
    }

    const handleExportPatientText = () => {
        if (!patientId) {
            toast.error(exportText.missingPatientDataId)
            return
        }

        exportPatientTextMutation.mutate(
            {
                patientId,
                format: textExportFormat,
                language,
            },
            {
                onSuccess: (result) => {
                    const fallbackName = buildDownloadName(
                        data?.patient?.full_name,
                        `patient-${patientId}.zip`
                    )
                    triggerFileDownload(result.blob, result.filename ?? fallbackName)
                    toast.success(
                        textExportFormat === "json"
                            ? exportText.exportTextSuccessJson
                            : exportText.exportTextSuccessPdf
                    )
                },
                onError: (err) => {
                    toast.error(getErrorMessage(err, exportText.exportTextFailed))
                },
            }
        )
    }

    const handleExportVitalSigns = () => {
        if (!patientId) {
            toast.error(exportText.missingPatientDataId)
            return
        }

        exportVitalSignsMutation.mutate(
            { patientId, format: vitalExportFormat, language },
            {
                onSuccess: (result) => {
                    const fallbackName = buildDownloadName(
                        data?.patient?.full_name,
                        `patient-${patientId}-vitals.${vitalExportFormat}`,
                        "-vitals"
                    )
                    triggerFileDownload(result.blob, result.filename ?? fallbackName)
                    toast.success(
                        language === "vi"
                            ? "Đã xuất dữ liệu sinh tồn."
                            : "Vital-sign data exported."
                    )
                },
                onError: (err) => {
                    toast.error(
                        getErrorMessage(
                            err,
                            language === "vi"
                                ? "Xuất dữ liệu sinh tồn thất bại."
                                : "Failed to export vital-sign data."
                        )
                    )
                },
            }
        )
    }

    const handleVitalImportButtonClick = () => {
        vitalImportInputRef.current?.click()
    }

    const handleVitalImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const selected = event.target.files?.[0] ?? null
        if (!selected) {
            return
        }

        const resetInput = () => {
            if (vitalImportInputRef.current) {
                vitalImportInputRef.current.value = ""
            }
        }

        if (!patientId) {
            toast.error(uiText.errors.missingPatientId)
            resetInput()
            return
        }

        const lowerName = selected.name.toLowerCase()
        if (!lowerName.endsWith(".json") && !lowerName.endsWith(".pdf")) {
            toast.error(
                language === "vi"
                    ? "Tệp nhập sinh tồn không hợp lệ. Chỉ hỗ trợ .json hoặc .pdf."
                    : "Invalid vital import file. Only .json or .pdf is supported."
            )
            resetInput()
            return
        }

        importVitalPreviewMutation.mutate(
            { patientId, file: selected },
            {
                onSuccess: (result) => {
                    const parsedPrefillNotes = parseTreatmentCheckupNotes(result.prefill.notes)
                    setEditingVitalId(null)
                    setVitalForm((prev) => ({
                        ...prev,
                        ...result.prefill,
                        source: (
                            result.prefill.source === "clinic"
                            || result.prefill.source === "hospital"
                            || result.prefill.source === "device"
                            || result.prefill.source === "self_reported"
                        )
                            ? result.prefill.source
                            : prev.source,
                        bloodGlucoseTiming: (
                            result.prefill.bloodGlucoseTiming === "fasting"
                            || result.prefill.bloodGlucoseTiming === "before_meal"
                            || result.prefill.bloodGlucoseTiming === "after_meal"
                            || result.prefill.bloodGlucoseTiming === "random"
                        )
                            ? result.prefill.bloodGlucoseTiming
                            : "",
                        reasonForVisit: parsedPrefillNotes.reasonForVisit || "",
                        testResultComment: parsedPrefillNotes.testResultComment || "",
                        patientProgress: parsedPrefillNotes.patientProgress || "",
                        treatmentPlan: parsedPrefillNotes.treatmentPlan || "",
                        doctorNotes: parsedPrefillNotes.doctorNotes || "",
                        notes: parsedPrefillNotes.plainNotes || result.prefill.notes || "",
                    }))
                    setIsCheckupFormVisible(true)
                    setVitalError(null)
                    setVitalSuccess(
                        language === "vi"
                            ? "Đã điền sẵn biểu mẫu từ tệp nhập. Vui lòng kiểm tra trước khi lưu."
                            : "Form prefilled from imported data. Review and edit before saving."
                    )
                    if (result.warning) {
                        toast.warning(result.warning)
                    } else {
                        toast.success(
                            language === "vi"
                                ? "Đã nhập dữ liệu sinh tồn để điền sẵn."
                                : "Vital-sign data imported for prefill."
                        )
                    }
                },
                onError: (err) => {
                    toast.error(
                        getErrorMessage(
                            err,
                            language === "vi"
                                ? "Nhập dữ liệu sinh tồn thất bại."
                                : "Failed to import vital-sign data."
                        )
                    )
                },
                onSettled: () => {
                    resetInput()
                },
            }
        )
    }

    const handleExportMedicalHistory = () => {
        if (!patientId) {
            toast.error(exportText.missingPatientDataId)
            return
        }

        exportMedicalHistoryMutation.mutate(
            { patientId, format: medicalHistoryExportFormat, language },
            {
                onSuccess: (result) => {
                    const fallbackName = buildDownloadName(
                        data?.patient?.full_name,
                        `patient-${patientId}-medical-history.${medicalHistoryExportFormat}`,
                        "-medical-history"
                    )
                    triggerFileDownload(result.blob, result.filename ?? fallbackName)
                    toast.success(
                        language === "vi"
                            ? "Đã xuất dữ liệu tiền sử y khoa."
                            : "Medical-history data exported."
                    )
                },
                onError: (err) => {
                    toast.error(
                        getErrorMessage(
                            err,
                            language === "vi"
                                ? "Xuất dữ liệu tiền sử y khoa thất bại."
                                : "Failed to export medical-history data."
                        )
                    )
                },
            }
        )
    }

    const handleMedicalHistoryImportButtonClick = () => {
        medicalHistoryImportInputRef.current?.click()
    }

    const handleMedicalHistoryImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const selected = event.target.files?.[0] ?? null
        if (!selected) {
            return
        }

        const resetInput = () => {
            if (medicalHistoryImportInputRef.current) {
                medicalHistoryImportInputRef.current.value = ""
            }
        }

        if (!patientId) {
            toast.error(uiText.errors.missingPatientId)
            resetInput()
            return
        }

        const lowerName = selected.name.toLowerCase()
        if (!lowerName.endsWith(".json") && !lowerName.endsWith(".pdf")) {
            toast.error(
                language === "vi"
                    ? "Tệp nhập tiền sử y khoa không hợp lệ. Chỉ hỗ trợ .json hoặc .pdf."
                    : "Invalid medical-history import file. Only .json or .pdf is supported."
            )
            resetInput()
            return
        }

        importMedicalHistoryPreviewMutation.mutate(
            { patientId, file: selected },
            {
                onSuccess: (result) => {
                    setMedicalHistoryForm(buildMedicalHistoryFormStateFromImportPrefill(result.prefill))
                    setMedicalHistoryError(null)
                    setMedicalHistorySuccess(
                        language === "vi"
                            ? "Biểu mẫu đã được điền sẵn từ tệp nhập. Vui lòng kiểm tra trước khi lưu."
                            : "Form prefilled from imported medical-history data. Review before saving."
                    )
                    setIsMedicalHistoryEditing(true)
                    if (result.warning) {
                        toast.warning(result.warning)
                    } else {
                        toast.success(
                            language === "vi"
                                ? "Đã nhập dữ liệu tiền sử y khoa để điền sẵn."
                                : "Medical-history data imported for prefill."
                        )
                    }
                },
                onError: (err) => {
                    toast.error(
                        getErrorMessage(
                            err,
                            language === "vi"
                                ? "Nhập dữ liệu tiền sử y khoa thất bại."
                                : "Failed to import medical-history data."
                        )
                    )
                },
                onSettled: () => {
                    resetInput()
                },
            }
        )
    }

    const handleImportButtonClick = () => {
        importInputRef.current?.click()
    }

    const handleImportProgress = (status: PatientTextImportStatusResponse) => {
        const nextProgress = Number.isFinite(status.progress) ? Math.max(0, Math.min(100, status.progress)) : 0
        setImportProgressValue(nextProgress)
        setImportProgressStage(status.stage || exportText.importing)
    }

    const handleImportFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        const selected = event.target.files?.[0] ?? null
        if (!selected) {
            return
        }

        const resetInput = () => {
            if (importInputRef.current) {
                importInputRef.current.value = ""
            }
        }

        if (!patientId) {
            toast.error(exportText.missingPatientImportId)
            resetInput()
            return
        }

        const lowerName = selected.name.toLowerCase()
        if (!lowerName.endsWith(".zip")) {
            toast.error(exportText.invalidImportFileType)
            resetInput()
            return
        }

        setIsImportProgressOpen(true)
        setImportProgressValue(2)
        setImportProgressStage(exportText.importing)

        importPatientTextMutation.mutate(
            { patientId, file: selected, onProgress: handleImportProgress },
            {
                onSuccess: (result) => {
                    setImportProgressValue(100)
                    setImportProgressStage(result.message || exportText.importSuccess)
                    toast.success(result.message || exportText.importSuccess)
                    if (result.warning) {
                        toast.warning(result.warning)
                    }
                    void refetchRecords()
                    window.setTimeout(() => {
                        setIsImportProgressOpen(false)
                        setImportProgressValue(0)
                        setImportProgressStage("")
                    }, 700)
                },
                onError: (err) => {
                    const message = getErrorMessage(err, exportText.importFailed)
                    setImportProgressStage(message)
                    toast.error(message)
                    window.setTimeout(() => {
                        setIsImportProgressOpen(false)
                        setImportProgressValue(0)
                        setImportProgressStage("")
                    }, 900)
                },
                onSettled: () => {
                    resetInput()
                },
            }
        )
    }

    const updateVitalForm = (key: keyof VitalFormState, value: string) => {
        setVitalForm(prev => ({
            ...prev,
            [key]: value,
        }))
    }

    const resetVitalForm = () => {
        setVitalForm({
            recordedAt: "",
            source: role === "doctor" ? "clinic" : "self_reported",
            bloodPressureSystolic: "",
            bloodPressureDiastolic: "",
            heartRate: "",
            bloodGlucose: "",
            bloodGlucoseTiming: "",
            temperature: "",
            oxygenSaturation: "",
            weightKg: "",
            reasonForVisit: "",
            testResultComment: "",
            patientProgress: "",
            treatmentPlan: "",
            doctorNotes: "",
            notes: "",
        })
    }

    const startEditCheckup = (vital: VitalSign) => {
        const parsedNotes = parseTreatmentCheckupNotes(vital.notes)
        setEditingVitalId(vital.id)
        setIsCheckupFormVisible(true)
        setVitalError(null)
        setVitalSuccess(null)
        setVitalForm({
            recordedAt: toDateTimeLocalValue(vital.recorded_at),
            source: vital.source || (role === "doctor" ? "clinic" : "self_reported"),
            bloodPressureSystolic: vital.blood_pressure_systolic?.toString() || "",
            bloodPressureDiastolic: vital.blood_pressure_diastolic?.toString() || "",
            heartRate: vital.heart_rate?.toString() || "",
            bloodGlucose: vital.blood_glucose?.toString() || "",
            bloodGlucoseTiming: vital.blood_glucose_timing || "",
            temperature: vital.temperature?.toString() || "",
            oxygenSaturation: vital.oxygen_saturation?.toString() || "",
            weightKg: vital.weight_kg?.toString() || "",
            reasonForVisit: parsedNotes.reasonForVisit || "",
            testResultComment: parsedNotes.testResultComment || "",
            patientProgress: parsedNotes.patientProgress || "",
            treatmentPlan: parsedNotes.treatmentPlan || "",
            doctorNotes: parsedNotes.doctorNotes || "",
            notes: parsedNotes.plainNotes || "",
        })
    }

    const handleStartAddCheckup = () => {
        setEditingVitalId(null)
        setVitalError(null)
        setVitalSuccess(null)
        resetVitalForm()
        setIsCheckupFormVisible(true)
    }

    const cancelEditCheckup = () => {
        setEditingVitalId(null)
        setVitalError(null)
        resetVitalForm()
        setIsCheckupFormVisible(false)
    }

    const buildVitalPayloadFromForm = (): VitalSignInput => ({
        recorded_at: vitalForm.recordedAt
            ? new Date(vitalForm.recordedAt).toISOString()
            : undefined,
        recorded_by: role === "doctor" ? user?.id : undefined,
        blood_pressure_systolic: vitalForm.bloodPressureSystolic
            ? Number.parseInt(vitalForm.bloodPressureSystolic, 10)
            : undefined,
        blood_pressure_diastolic: vitalForm.bloodPressureDiastolic
            ? Number.parseInt(vitalForm.bloodPressureDiastolic, 10)
            : undefined,
        heart_rate: vitalForm.heartRate
            ? Number.parseInt(vitalForm.heartRate, 10)
            : undefined,
        blood_glucose: vitalForm.bloodGlucose
            ? Number.parseFloat(vitalForm.bloodGlucose)
            : undefined,
        blood_glucose_timing: vitalForm.bloodGlucoseTiming
            ? (vitalForm.bloodGlucoseTiming as VitalSignInput["blood_glucose_timing"])
            : undefined,
        temperature: vitalForm.temperature
            ? Number.parseFloat(vitalForm.temperature)
            : undefined,
        oxygen_saturation: vitalForm.oxygenSaturation
            ? Number.parseInt(vitalForm.oxygenSaturation, 10)
            : undefined,
        weight_kg: vitalForm.weightKg
            ? Number.parseFloat(vitalForm.weightKg)
            : undefined,
        notes: buildTreatmentCheckupNotes(vitalForm),
        source: vitalForm.source
            ? (vitalForm.source as VitalSignInput["source"])
            : undefined,
    })

    const handleDeleteCheckup = () => {
        if (!patientId || !deleteVital) {
            return
        }

        deleteVitalMutation.mutate(
            { patientId, vitalId: deleteVital.id },
            {
                onSuccess: () => {
                    if (editingVitalId === deleteVital.id) {
                        setEditingVitalId(null)
                        resetVitalForm()
                        setIsCheckupFormVisible(false)
                    }
                    setDeleteVital(null)
                    setVitalError(null)
                    setVitalSuccess(
                        language === "vi"
                            ? "Đã xóa lần khám."
                            : "Check-up deleted."
                    )
                },
                onError: (err) => {
                    setVitalError(
                        getErrorMessage(
                            err,
                            language === "vi"
                                ? "Xóa lần khám thất bại."
                                : "Failed to delete check-up."
                        )
                    )
                },
            }
        )
    }

    const handleVitalSubmit = () => {
        setVitalError(null)
        setVitalSuccess(null)

        if (!patientId) {
            setVitalError(uiText.errors.missingPatientId)
            return
        }

        const hasMeasurements = [
            vitalForm.bloodPressureSystolic,
            vitalForm.bloodPressureDiastolic,
            vitalForm.heartRate,
            vitalForm.bloodGlucose,
            vitalForm.temperature,
            vitalForm.oxygenSaturation,
            vitalForm.weightKg,
        ].some(value => value.trim() !== "")

        if (!hasMeasurements) {
            setVitalError(uiText.errors.enterAtLeastOneVital)
            return
        }

        const payload = buildVitalPayloadFromForm()

        if (editingVitalId) {
            updateVitalMutation.mutate(
                { patientId, vitalId: editingVitalId, data: payload },
                {
                    onSuccess: () => {
                        setVitalSuccess(
                            language === "vi"
                                ? "Đã cập nhật lần khám."
                                : "Check-up updated."
                        )
                        setEditingVitalId(null)
                        resetVitalForm()
                        setIsCheckupFormVisible(false)
                    },
                    onError: (err) => {
                        setVitalError(
                            getErrorMessage(
                                err,
                                language === "vi"
                                    ? "Cập nhật lần khám thất bại."
                                    : "Failed to update check-up."
                            )
                        )
                    },
                }
            )
            return
        }

        createVitalMutation.mutate(
            { patientId, data: payload },
            {
                onSuccess: () => {
                    setVitalSuccess(uiText.vitalSaveSuccess)
                    resetVitalForm()
                    setIsCheckupFormVisible(false)
                },
            }
        )
    }

    if (isLoading) {
        return <LoadingOverlay text={uiText.loadingPatient} />
    }

    if (error || !data?.patient) {
        return (
            <Card className="border-destructive/30 bg-destructive/5">
                <CardContent className="p-6 text-center">
                    <p className="text-destructive font-medium">{uiText.loadPatientErrorTitle}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                        {uiText.loadPatientErrorHint}
                    </p>
                </CardContent>
            </Card>
        )
    }

    const patient = data.patient
    const initials = getInitials(patient.full_name)
    const historySections = buildPatientHistorySections(patient, language)
    const vitals = (vitalsData?.vitals ?? data.recent_vitals).slice().sort((a, b) => {
        const aTime = new Date(a.recorded_at).getTime()
        const bTime = new Date(b.recorded_at).getTime()
        if (Number.isNaN(aTime) || Number.isNaN(bTime)) return 0
        return bTime - aTime
    })
    const treatmentMedicalRecords = (recordsData?.records ?? []).filter((record) =>
        TEST_RESULT_RECORD_TYPES.has(record.record_type)
    )
    const checkupRecordGroups = groupMedicalRecordsByCheckup(vitals, treatmentMedicalRecords)
    const unlinkedMedicalRecords = checkupRecordGroups.unlinkedRecords
    const selectedCheckupForUpload = selectedCheckupForUploadId
        ? vitals.find((vital) => vital.id === selectedCheckupForUploadId) ?? null
        : null
    const postUploadRecord = postUploadRecordId
        ? recordsData?.records.find((record) => record.id === postUploadRecordId)
        : null
    const postUploadAnalysis = postUploadAiAnalysis ?? postUploadRecord?.analysis_result ?? null
    const isMedicalHistorySaving = updatePatientMutation.isPending
    const metadataText = language === "vi"
        ? {
            dateOfBirth: "Ngày sinh",
            gender: "Giới tính",
            nric: "Số CCCD",
            insuranceNumber: "Mã số BHYT",
            diagnosis: "Chẩn đoán",
            email: "Email",
            address: "Địa chỉ",
            emergencyContact: "Liên hệ khẩn cấp",
            unknown: "--",
        }
        : {
            dateOfBirth: "Date of birth",
            gender: "Gender",
            nric: "NRIC",
            insuranceNumber: "Health insurance number",
            diagnosis: "Diagnosis",
            email: "Email",
            address: "Address",
            emergencyContact: "Emergency contact",
            unknown: "--",
        }
    const genderLabel = patient.gender === "male"
        ? (language === "vi" ? "Nam" : "Male")
        : patient.gender === "female"
            ? (language === "vi" ? "Nữ" : "Female")
            : patient.gender === "other"
                ? (language === "vi" ? "Khác" : "Other")
                : metadataText.unknown
    const formattedDateOfBirth = patient.date_of_birth
        ? (() => {
            const parsed = new Date(patient.date_of_birth)
            return Number.isNaN(parsed.getTime())
                ? patient.date_of_birth
                : parsed.toLocaleDateString(uiText.locale)
        })()
        : metadataText.unknown
    const address = [
        patient.address_ward,
        patient.address_district,
        patient.address_province,
    ].filter((item) => typeof item === "string" && item.trim() !== "").join(", ") || metadataText.unknown
    const emergencyContact = [
        patient.emergency_contact_name,
        patient.emergency_contact_phone,
    ].filter((item) => typeof item === "string" && item.trim() !== "").join(" - ") || metadataText.unknown
    const patientMetadataItems = [
        { label: metadataText.dateOfBirth, value: formattedDateOfBirth },
        { label: metadataText.gender, value: genderLabel },
        { label: metadataText.nric, value: patient.national_id || metadataText.unknown },
        { label: metadataText.insuranceNumber, value: patient.insurance_number || metadataText.unknown },
        { label: metadataText.diagnosis, value: patient.primary_diagnosis || metadataText.unknown },
        { label: metadataText.email, value: patient.email || metadataText.unknown },
        { label: metadataText.address, value: address },
        { label: metadataText.emergencyContact, value: emergencyContact },
    ]

    const handleStartMedicalHistoryEdit = () => {
        setMedicalHistoryForm(buildMedicalHistoryFormState(patient))
        setMedicalHistoryError(null)
        setMedicalHistorySuccess(null)
        setIsMedicalHistoryEditing(true)
    }

    const handleCancelMedicalHistoryEdit = () => {
        setMedicalHistoryForm(buildMedicalHistoryFormState(patient))
        setMedicalHistoryError(null)
        setIsMedicalHistoryEditing(false)
    }

    const updateMedicalHistoryEntry = (field: MedicalHistoryFieldKey, index: number, value: string) => {
        setMedicalHistoryForm((prev) => {
            const next = [...(prev[field] ?? [])]
            while (next.length <= index) {
                next.push("")
            }
            next[index] = value
            return {
                ...prev,
                [field]: next,
            }
        })
    }

    const addMedicalHistoryEntry = (field: MedicalHistoryFieldKey) => {
        setMedicalHistoryForm((prev) => ({
            ...prev,
            [field]: [...(prev[field] ?? []), ""],
        }))
    }

    const removeMedicalHistoryEntry = (field: MedicalHistoryFieldKey, index: number) => {
        setMedicalHistoryForm((prev) => ({
            ...prev,
            [field]: (prev[field] ?? []).filter((_, itemIndex) => itemIndex !== index),
        }))
    }

    const handleSaveMedicalHistory = () => {
        if (!patientId) {
            setMedicalHistoryError(uiText.errors.missingPatientId)
            setMedicalHistorySuccess(null)
            return
        }

        const payload = buildMedicalHistoryUpdatePayload(medicalHistoryForm, patient)
        updatePatientMutation.mutate(
            { patientId, data: payload },
            {
                onSuccess: () => {
                    setMedicalHistoryError(null)
                    setMedicalHistorySuccess(
                        language === "vi"
                            ? "Đã cập nhật tiền sử y khoa."
                            : "Medical history updated successfully."
                    )
                    setIsMedicalHistoryEditing(false)
                },
                onError: (err) => {
                    setMedicalHistorySuccess(null)
                    setMedicalHistoryError(
                        getErrorMessage(
                            err,
                            language === "vi"
                                ? "Không thể cập nhật tiền sử y khoa."
                                : "Failed to update medical history."
                        )
                    )
                },
            }
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div className="flex items-center gap-3">
                    <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/patients")}>
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        {uiText.backButton}
                    </Button>
                    <PageHeader title={uiText.pageTitle} description={patient.full_name} />
                </div>
                <div className="w-full space-y-2 md:w-auto md:pt-1">
                    <input
                        ref={importInputRef}
                        type="file"
                        accept=".zip,application/zip"
                        className="hidden"
                        onChange={handleImportFileChange}
                    />
                    <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                        <div className="flex w-full sm:w-auto">
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="rounded-r-none border-r-0"
                                onClick={handleExportPatientText}
                                disabled={
                                    exportPatientTextMutation.isPending
                                    || importPatientTextMutation.isPending
                                }
                            >
                                <FileText className="h-4 w-4 mr-2" />
                                {exportPatientTextMutation.isPending ? exportText.exporting : exportText.exportTextButton}
                            </Button>
                            <select
                                aria-label={exportText.formatAriaLabel}
                                value={textExportFormat}
                                onChange={(event) => setTextExportFormat(event.target.value as TextExportFormat)}
                                disabled={
                                    exportPatientTextMutation.isPending
                                    || importPatientTextMutation.isPending
                                }
                                className="border-input h-9 w-24 rounded-l-none rounded-r-md border bg-transparent px-2 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
                            >
                                <option value="json">JSON</option>
                                <option value="pdf">PDF</option>
                            </select>
                        </div>
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={handleImportButtonClick}
                            disabled={
                                exportPatientTextMutation.isPending
                                || importPatientTextMutation.isPending
                            }
                        >
                            <Upload className="h-4 w-4 mr-2" />
                            {importPatientTextMutation.isPending ? exportText.importing : exportText.importTextButton}
                        </Button>
                    </div>
                    <p className="text-xs text-muted-foreground sm:text-right">
                        {exportText.exportHint}
                    </p>
                </div>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>{uiText.photoCardTitle}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center gap-4">
                        <Avatar className="h-16 w-16">
                            {patient.profile_photo_url && (
                                <AvatarImage
                                    src={patient.profile_photo_url}
                                    alt={patient.full_name}
                                />
                            )}
                            <AvatarFallback className="bg-primary/10 text-primary font-medium">
                                {initials}
                            </AvatarFallback>
                        </Avatar>
                        <div className="text-sm text-muted-foreground">
                            <p>{patient.full_name}</p>
                            <p>{patient.phone_primary}</p>
                        </div>
                    </div>
                    <div className="grid gap-2 rounded-lg border p-3 sm:grid-cols-2 sm:gap-3">
                        {patientMetadataItems.map((item) => (
                            <div
                                key={item.label}
                                className="rounded-md bg-muted/20 px-3 py-2"
                            >
                                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                                    {item.label}
                                </p>
                                <p className="text-sm text-foreground break-words">
                                    {item.value}
                                </p>
                            </div>
                        ))}
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="patient-photo">{uiText.patientPhotoUploadLabel}</Label>
                        <Input
                            id="patient-photo"
                            type="file"
                            accept="image/*"
                            onChange={handleFileChange}
                            ref={photoInputRef}
                        />
                    </div>

                    {photoError && (
                        <p className="text-sm text-destructive">{photoError}</p>
                    )}
                    {photoUploadMutation.isError && (
                        <p className="text-sm text-destructive">
                            {uiText.photoUploadFailed}
                        </p>
                    )}
                    {photoUploadMutation.isSuccess && (
                        <p className="text-sm text-emerald-600">
                            {uiText.photoUpdateSuccess}
                        </p>
                    )}

                    <Button
                        onClick={handleUpload}
                        disabled={!photoFile || photoUploadMutation.isPending}
                    >
                        <Upload className="h-4 w-4 mr-2" />
                        {photoUploadMutation.isPending ? uiText.uploadingLabel : uiText.photoUploadButton}
                    </Button>
                </CardContent>
            </Card>

            {/* Clinical Summary Card */}
            <Card className="overflow-hidden border-0 shadow-lg">
                <div className="bg-gradient-to-r from-teal-500/10 via-emerald-500/10 to-cyan-500/10 border-b">
                    <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 shadow-md shadow-teal-500/25">
                                <Sparkles className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <CardTitle className="text-lg">{uiText.summaryCardTitle}</CardTitle>
                                <p className="text-xs text-muted-foreground mt-0.5">{uiText.summaryCardSubtitle}</p>
                            </div>
                        </div>
                        <Button
                            type="button"
                            size="sm"
                            onClick={() => {
                                if (!patientId) return
                                summaryMutation.mutate(
                                    { patientId },
                                    {
                                        onSuccess: (data) => {
                                            setSummaryText(data.summary)
                                            setSummaryMeta({
                                                generated_at: data.generated_at,
                                                model: data.model,
                                            })
                                        },
                                        onError: () => {
                                            toast.error(uiText.summaryError)
                                        },
                                    }
                                )
                            }}
                            disabled={summaryMutation.isPending}
                            className={summaryText
                                ? "bg-muted text-muted-foreground hover:bg-muted/80"
                                : "bg-gradient-to-r from-teal-500 to-emerald-600 text-white hover:from-teal-600 hover:to-emerald-700 shadow-md shadow-teal-500/25"
                            }
                        >
                            {summaryMutation.isPending ? (
                                <>
                                    <RotateCw className="h-4 w-4 mr-2 animate-spin" />
                                    {uiText.summaryGenerating}
                                </>
                            ) : summaryText ? (
                                <>
                                    <RotateCw className="h-4 w-4 mr-2" />
                                    {uiText.summaryRegenerateButton}
                                </>
                            ) : (
                                <>
                                    <Sparkles className="h-4 w-4 mr-2" />
                                    {uiText.summaryGenerateButton}
                                </>
                            )}
                        </Button>
                    </CardHeader>
                </div>
                <CardContent className="pt-5">
                    {summaryMutation.isPending && (
                        <div className="flex flex-col items-center justify-center py-12 gap-4">
                            <div className="relative">
                                <div className="h-12 w-12 rounded-full border-2 border-teal-200 border-t-teal-500 animate-spin" />
                                <Sparkles className="h-5 w-5 text-teal-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                            </div>
                            <div className="text-center">
                                <p className="text-sm font-medium text-foreground">{uiText.summaryGenerating}</p>
                                <p className="text-xs text-muted-foreground mt-1">{uiText.summaryGeneratingHint}</p>
                            </div>
                        </div>
                    )}
                    {!summaryMutation.isPending && summaryText && (
                        <div className="space-y-4">
                            <div className="text-sm leading-relaxed markdown-content clinical-summary-content">
                                <ReactMarkdown>{formattedSummaryText}</ReactMarkdown>
                            </div>
                            {summaryMeta && (
                                <div className="flex items-center gap-4 pt-3 border-t border-border/50 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1.5">
                                        <Clock className="h-3 w-3" />
                                        {uiText.summaryTimestamp}: {new Date(summaryMeta.generated_at).toLocaleString(uiText.locale)}
                                    </span>
                                    <span className="flex items-center gap-1.5">
                                        <Monitor className="h-3 w-3" />
                                        {uiText.summaryModel}: {summaryMeta.model}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                    {!summaryMutation.isPending && !summaryText && (
                        <div className="flex flex-col items-center justify-center py-10 gap-3 text-center">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-50 to-emerald-50 dark:from-teal-950/30 dark:to-emerald-950/30">
                                <Sparkles className="h-7 w-7 text-teal-500/60" />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">
                                    {language === "vi"
                                        ? "Nhấn nút để AI tạo tóm tắt lâm sàng từ dữ liệu hồ sơ bệnh nhân."
                                        : "Click the button to generate an AI clinical summary from patient data."}
                                </p>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <CardTitle>{uiText.vitalsCardTitle}</CardTitle>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <input
                            ref={vitalImportInputRef}
                            type="file"
                            accept=".json,.pdf,application/json,application/pdf"
                            className="hidden"
                            onChange={handleVitalImportFileChange}
                        />
                        <Button
                            type="button"
                            size="sm"
                            onClick={handleStartAddCheckup}
                            disabled={createVitalMutation.isPending || updateVitalMutation.isPending || deleteVitalMutation.isPending}
                        >
                            {language === "vi" ? "Thêm lần khám" : "Add check-up"}
                        </Button>
                        <div className="flex w-full sm:w-auto">
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="rounded-r-none border-r-0"
                                onClick={handleExportVitalSigns}
                                disabled={exportVitalSignsMutation.isPending || importVitalPreviewMutation.isPending}
                            >
                                <FileText className="mr-2 h-4 w-4" />
                                {exportVitalSignsMutation.isPending
                                    ? exportText.exporting
                                    : (language === "vi" ? "Xuất dữ liệu sinh tồn" : "Export vital signs")}
                            </Button>
                            <select
                                aria-label={language === "vi" ? "Định dạng xuất sinh tồn" : "Vital export format"}
                                value={vitalExportFormat}
                                onChange={(event) => setVitalExportFormat(event.target.value as TextExportFormat)}
                                disabled={exportVitalSignsMutation.isPending || importVitalPreviewMutation.isPending}
                                className="border-input h-9 w-24 rounded-l-none rounded-r-md border bg-transparent px-2 py-1 text-sm shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:opacity-50"
                            >
                                <option value="json">JSON</option>
                                <option value="pdf">PDF</option>
                            </select>
                        </div>
                        <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={handleVitalImportButtonClick}
                            disabled={exportVitalSignsMutation.isPending || importVitalPreviewMutation.isPending}
                        >
                            <Upload className="mr-2 h-4 w-4" />
                            {importVitalPreviewMutation.isPending
                                ? exportText.importing
                                : (language === "vi" ? "Nhập dữ liệu sinh tồn" : "Import vital signs")}
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className={`grid gap-6 ${isCheckupFormVisible ? "lg:grid-cols-2" : "lg:grid-cols-1"}`}>
                        {isCheckupFormVisible && (
                        <div className="space-y-4">
                            <div className="grid gap-3 md:grid-cols-2">
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-recorded-at">{uiText.vitalRecordedAtLabel}</Label>
                                    <Input
                                        id="vital-recorded-at"
                                        type="datetime-local"
                                        value={vitalForm.recordedAt}
                                        onChange={(event) => updateVitalForm("recordedAt", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-source">{uiText.vitalSourceLabel}</Label>
                                    <select
                                        id="vital-source"
                                        value={vitalForm.source}
                                        onChange={(event) => updateVitalForm("source", event.target.value)}
                                        className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                    >
                                        {vitalSourceOptions.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-bp-sys">{uiText.vitalBpSystolicLabel}</Label>
                                    <Input
                                        id="vital-bp-sys"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="120"
                                        value={vitalForm.bloodPressureSystolic}
                                        onChange={(event) => updateVitalForm("bloodPressureSystolic", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-bp-dia">{uiText.vitalBpDiastolicLabel}</Label>
                                    <Input
                                        id="vital-bp-dia"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="80"
                                        value={vitalForm.bloodPressureDiastolic}
                                        onChange={(event) => updateVitalForm("bloodPressureDiastolic", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-heart-rate">{uiText.vitalHeartRateLabel}</Label>
                                    <Input
                                        id="vital-heart-rate"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="72"
                                        value={vitalForm.heartRate}
                                        onChange={(event) => updateVitalForm("heartRate", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-spo2">{uiText.vitalSpo2Label}</Label>
                                    <Input
                                        id="vital-spo2"
                                        type="number"
                                        inputMode="numeric"
                                        placeholder="98"
                                        value={vitalForm.oxygenSaturation}
                                        onChange={(event) => updateVitalForm("oxygenSaturation", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-temperature">{uiText.vitalTemperatureLabel}</Label>
                                    <Input
                                        id="vital-temperature"
                                        type="number"
                                        inputMode="decimal"
                                        step="0.1"
                                        placeholder="36.6"
                                        value={vitalForm.temperature}
                                        onChange={(event) => updateVitalForm("temperature", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-weight">{uiText.vitalWeightLabel}</Label>
                                    <Input
                                        id="vital-weight"
                                        type="number"
                                        inputMode="decimal"
                                        step="0.1"
                                        placeholder="60"
                                        value={vitalForm.weightKg}
                                        onChange={(event) => updateVitalForm("weightKg", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-glucose">{uiText.vitalBloodGlucoseLabel}</Label>
                                    <Input
                                        id="vital-glucose"
                                        type="number"
                                        inputMode="decimal"
                                        step="0.1"
                                        placeholder="5.6"
                                        value={vitalForm.bloodGlucose}
                                        onChange={(event) => updateVitalForm("bloodGlucose", event.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="vital-glucose-timing">{uiText.vitalGlucoseTimingLabel}</Label>
                                    <select
                                        id="vital-glucose-timing"
                                        value={vitalForm.bloodGlucoseTiming}
                                        onChange={(event) => updateVitalForm("bloodGlucoseTiming", event.target.value)}
                                        className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                    >
                                        {glucoseTimingOptions.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-reason-visit">
                                        {language === "vi" ? "Lý do khám" : "Reason for visit"}
                                    </Label>
                                    <Textarea
                                        id="vital-reason-visit"
                                        value={vitalForm.reasonForVisit}
                                        onChange={(event) => updateVitalForm("reasonForVisit", event.target.value)}
                                        rows={2}
                                    />
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-test-comment">
                                        {language === "vi" ? "Nhận xét kết quả xét nghiệm" : "Doctor comments on test results"}
                                    </Label>
                                    <Textarea
                                        id="vital-test-comment"
                                        value={vitalForm.testResultComment}
                                        onChange={(event) => updateVitalForm("testResultComment", event.target.value)}
                                        rows={2}
                                    />
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-progress">
                                        {language === "vi" ? "Tiến triển bệnh nhân" : "Patient progress"}
                                    </Label>
                                    <Textarea
                                        id="vital-progress"
                                        value={vitalForm.patientProgress}
                                        onChange={(event) => updateVitalForm("patientProgress", event.target.value)}
                                        rows={2}
                                    />
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-treatment-plan">
                                        {language === "vi" ? "Kế hoạch điều trị" : "Treatment plan"}
                                    </Label>
                                    <Textarea
                                        id="vital-treatment-plan"
                                        value={vitalForm.treatmentPlan}
                                        onChange={(event) => updateVitalForm("treatmentPlan", event.target.value)}
                                        rows={2}
                                    />
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-doctor-notes">
                                        {language === "vi" ? "Ghi chú bác sĩ" : "Doctor notes"}
                                    </Label>
                                    <Textarea
                                        id="vital-doctor-notes"
                                        value={vitalForm.doctorNotes}
                                        onChange={(event) => updateVitalForm("doctorNotes", event.target.value)}
                                        rows={2}
                                    />
                                </div>
                                <div className="grid gap-2 md:col-span-2">
                                    <Label htmlFor="vital-notes">{uiText.vitalNotesLabel}</Label>
                                    <Textarea
                                        id="vital-notes"
                                        placeholder={uiText.vitalNotesPlaceholder}
                                        value={vitalForm.notes}
                                        onChange={(event) => updateVitalForm("notes", event.target.value)}
                                        rows={3}
                                    />
                                </div>
                            </div>

                            {vitalError && (
                                <p className="text-sm text-destructive">{vitalError}</p>
                            )}
                            {createVitalMutation.isError && (
                                <p className="text-sm text-destructive">
                                    {uiText.vitalSaveFailed}
                                </p>
                            )}
                            {vitalSuccess && (
                                <p className="text-sm text-emerald-600">{vitalSuccess}</p>
                            )}

                            <div className="flex flex-wrap gap-2">
                                <Button
                                    onClick={handleVitalSubmit}
                                    disabled={createVitalMutation.isPending || updateVitalMutation.isPending || deleteVitalMutation.isPending}
                                >
                                    <Activity className="h-4 w-4 mr-2" />
                                    {(createVitalMutation.isPending || updateVitalMutation.isPending)
                                        ? uiText.savingLabel
                                        : (editingVitalId
                                            ? (language === "vi" ? "Cập nhật lần khám" : "Update check-up")
                                            : uiText.vitalSaveButton)}
                                </Button>
                                {isCheckupFormVisible && (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={cancelEditCheckup}
                                        disabled={createVitalMutation.isPending || updateVitalMutation.isPending}
                                    >
                                        {uiText.cancelButton}
                                    </Button>
                                )}
                            </div>
                        </div>
                        )}

                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <p className="text-sm font-medium text-foreground">{uiText.recentHistoryLabel}</p>
                                <Badge variant="secondary">{checkupRecordGroups.groups.length} {uiText.recordCountSuffix}</Badge>
                            </div>

                            <div className="w-full sm:w-56">
                                <Label htmlFor="record-filter" className="sr-only">
                                    {exportText.filterAriaLabel}
                                </Label>
                                <select
                                    id="record-filter"
                                    value={recordFilter}
                                    onChange={(event) => setRecordFilter(event.target.value)}
                                    className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                >
                                    {recordTypeOptions.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {vitalsLoading && checkupRecordGroups.groups.length === 0 && (
                                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                                    {uiText.vitalsLoading}
                                </div>
                            )}

                            {vitalsError && (
                                <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                                    {uiText.vitalsLoadFailed}
                                </div>
                            )}

                            {!vitalsLoading && !vitalsError && checkupRecordGroups.groups.length === 0 && (
                                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                                    {uiText.vitalsEmpty}
                                </div>
                            )}

                            {!vitalsError && checkupRecordGroups.groups.length > 0 && (
                                <div className="space-y-3">
                                    {checkupRecordGroups.groups.map((group, index) => {
                                        const vital = group.vital
                                        const metrics = formatVitalMetrics(vital, uiText)
                                        const checkupNotes = parseTreatmentCheckupNotes(vital.notes)
                                        const checkupTitle = language === "vi"
                                            ? `Lần khám ${checkupRecordGroups.groups.length - index}`
                                            : `Check-up ${checkupRecordGroups.groups.length - index}`
                                        return (
                                            <div key={vital.id} className="rounded-lg border p-4">
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <div>
                                                        <p className="text-sm font-semibold text-foreground">{checkupTitle}</p>
                                                        <p className="text-sm text-foreground">
                                                            {formatDateTime(vital.recorded_at, uiText.locale)}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground">
                                                            {formatVitalSource(vital.source, uiText)}
                                                        </p>
                                                    </div>
                                                    <div className="flex flex-wrap items-center gap-2">
                                                        {vital.source && (
                                                            <Badge variant="outline">
                                                                {formatVitalSource(vital.source, uiText)}
                                                            </Badge>
                                                        )}
                                                        <Button
                                                            type="button"
                                                            size="sm"
                                                            variant="outline"
                                                            onClick={() => openRecordUploadDialog(vital.id)}
                                                        >
                                                            <Upload className="mr-2 h-4 w-4" />
                                                            {language === "vi" ? "Tải tệp y khoa" : "Upload medical files"}
                                                        </Button>
                                                        {role === "doctor" && (
                                                            <>
                                                                <Button
                                                                    type="button"
                                                                    size="sm"
                                                                    variant="outline"
                                                                    onClick={() => startEditCheckup(vital)}
                                                                >
                                                                    {uiText.editButton}
                                                                </Button>
                                                                <Button
                                                                    type="button"
                                                                    size="sm"
                                                                    variant="destructive"
                                                                    onClick={() => setDeleteVital(vital)}
                                                                >
                                                                    {uiText.deleteButton}
                                                                </Button>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                                {metrics.length > 0 && (
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        {metrics.map((metric) => (
                                                            <Badge key={metric} variant="secondary" className="text-xs">
                                                                {metric}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
                                                {vital.notes && formatVitalNotes(vital.notes) && (
                                                    <p className="mt-3 whitespace-pre-wrap break-all rounded-md bg-muted/40 px-2 py-1.5 font-mono text-xs text-muted-foreground">
                                                        {formatVitalNotes(vital.notes)}
                                                    </p>
                                                )}
                                                {checkupNotes.treatmentPlan && (
                                                    <p className="mt-1 text-xs text-muted-foreground">
                                                        <span className="font-medium text-foreground">
                                                            {language === "vi" ? "Kế hoạch điều trị: " : "Treatment plan: "}
                                                        </span>
                                                        {checkupNotes.treatmentPlan}
                                                    </p>
                                                )}
                                                {checkupNotes.doctorNotes && (
                                                    <p className="mt-1 text-xs text-muted-foreground">
                                                        <span className="font-medium text-foreground">
                                                            {language === "vi" ? "Ghi chú bác sĩ: " : "Doctor notes: "}
                                                        </span>
                                                        {checkupNotes.doctorNotes}
                                                    </p>
                                                )}
                                                {checkupNotes.plainNotes && (
                                                    <p className="mt-1 text-xs text-muted-foreground">
                                                        {checkupNotes.plainNotes}
                                                    </p>
                                                )}
                                                <div className="mt-4 rounded-md border bg-muted/20 p-3">
                                                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                                        {language === "vi" ? "Kết quả cận lâm sàng" : "Medical test results"}
                                                    </p>
                                                    {recordsLoading && (
                                                        <p className="mt-2 text-xs text-muted-foreground">{uiText.recordsLoading}</p>
                                                    )}
                                                    {!recordsLoading && !recordsError && group.records.length === 0 && (
                                                        <p className="mt-2 text-xs text-muted-foreground">
                                                            {language === "vi"
                                                                ? "Chưa có kết quả xét nghiệm được liên kết với lần khám này."
                                                                : "No linked medical test results for this check-up yet."}
                                                        </p>
                                                    )}
                                                    {!recordsLoading && !recordsError && group.records.length > 0 && (
                                                        <div className="mt-3 space-y-3">
                                                            {group.records.map((record) => (
                                                                <div key={record.id} className="rounded-md border bg-background p-3">
                                                                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                                                        <div className="min-w-0">
                                                                            <div className="flex flex-wrap items-center gap-2">
                                                                                <Badge variant="secondary">
                                                                                    {recordTypeLabels[record.record_type] ?? record.record_type}
                                                                                </Badge>
                                                                                {record.is_verified && (
                                                                                    <Badge variant="outline">{uiText.recordVerifiedBadge}</Badge>
                                                                                )}
                                                                            </div>
                                                                            <p className="mt-2 text-sm font-semibold text-foreground">
                                                                                {record.title}
                                                                            </p>
                                                                            <p className="text-xs text-muted-foreground">
                                                                                {formatDateTime(record.created_at, uiText.locale)}
                                                                            </p>
                                                                            {record.content_text && !hasAnalysis(record.analysis_result) && (
                                                                                <p className="mt-2 text-sm text-muted-foreground">
                                                                                    {truncateText(record.content_text, 180)}
                                                                                </p>
                                                                            )}
                                                                            <DoctorTestResultSummary doctorComment={record.doctor_comment} language={language} />
                                                                            <RecordAIAnalysis analysis={record.analysis_result} />
                                                                        </div>
                                                                        <div className="flex flex-col gap-2 items-start md:items-end">
                                                                            {role === "doctor" && (
                                                                                <div className="flex w-full flex-wrap justify-end gap-2 pb-1">
                                                                                    <Button
                                                                                        size="sm"
                                                                                        variant="outline"
                                                                                        onClick={() => openEditRecord(record)}
                                                                                    >
                                                                                        {uiText.editButton}
                                                                                    </Button>
                                                                                    <Button
                                                                                        size="sm"
                                                                                        variant="destructive"
                                                                                        onClick={() => {
                                                                                            setRecordListError(null)
                                                                                            setDeleteRecord(record)
                                                                                        }}
                                                                                    >
                                                                                        {uiText.deleteButton}
                                                                                    </Button>
                                                                                </div>
                                                                            )}
                                                                            {record.file_kind === "image" && record.file_url && (
                                                                                <button
                                                                                    type="button"
                                                                                    onClick={() => setActiveRecord(record)}
                                                                                    className="rounded-lg border overflow-hidden hover:ring-2 hover:ring-primary/30 transition"
                                                                                >
                                                                                    <img
                                                                                        src={record.file_url}
                                                                                        alt={record.title}
                                                                                        className="h-20 w-28 object-cover"
                                                                                    />
                                                                                </button>
                                                                            )}
                                                                            {record.file_kind === "pdf" && record.file_url && (
                                                                                <Button size="sm" variant="outline" asChild>
                                                                                    <a href={record.file_url} target="_blank" rel="noreferrer">
                                                                                        {uiText.downloadPdf}
                                                                                    </a>
                                                                                </Button>
                                                                            )}
                                                                            {!record.file_url && (
                                                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                                                    <FileText className="h-4 w-4" />
                                                                                    <span>{uiText.noAttachment}</span>
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )
                                    })}
                                    {!recordsLoading && !recordsError && unlinkedMedicalRecords.length > 0 && (
                                        <div className="rounded-lg border border-dashed p-3">
                                            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                                {language === "vi" ? "Kết quả chưa liên kết" : "Unlinked medical test results"}
                                            </p>
                                            <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                                                {unlinkedMedicalRecords.map((record) => (
                                                    <li key={record.id}>
                                                        {record.title} ({formatDateTime(record.created_at, uiText.locale)})
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                            {recordsError && (
                                <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                                    {uiText.recordsLoadFailed}
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {false && (
            <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <CardTitle>
                            {language === "vi" ? "Hồ sơ điều trị - Kết quả cận lâm sàng" : "Treatment Records - Medical Test Results"}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                            {language === "vi"
                                ? "Chỉ hiển thị kết quả xét nghiệm và chẩn đoán hình ảnh (lab, X-ray, ECG, CT, MRI)."
                                : "Only test-result records are shown here (lab, X-ray, ECG, CT, MRI)."}
                        </p>
                    </div>
                    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center md:w-auto md:justify-end">
                        <Button
                            type="button"
                            onClick={() => {
                                openRecordUploadDialog()
                            }}
                        >
                            <Upload className="mr-2 h-4 w-4" />
                            {language === "vi" ? "Tải tệp y khoa" : "Upload medical files"}
                        </Button>
                        <div className="w-full sm:w-56">
                            <Label htmlFor="record-filter" className="sr-only">
                                {exportText.filterAriaLabel}
                            </Label>
                            <select
                                id="record-filter"
                                value={recordFilter}
                                onChange={(event) => setRecordFilter(event.target.value)}
                                className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                            >
                                {recordTypeOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {recordListError && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                            {recordListError}
                        </div>
                    )}

                    {recordsLoading && (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            {uiText.recordsLoading}
                        </div>
                    )}

                    {recordsError && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                            {uiText.recordsLoadFailed}
                        </div>
                    )}

                    {!recordsLoading && !recordsError && treatmentMedicalRecords.length === 0 && (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            {uiText.recordsEmpty}
                        </div>
                    )}

                    {!recordsLoading && !recordsError && treatmentMedicalRecords.length > 0 && (
                        <div className="space-y-3">
                            {treatmentMedicalRecords.map((record) => (
                                <div key={record.id} className="rounded-lg border p-4">
                                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <Badge variant="secondary">
                                                    {recordTypeLabels[record.record_type] ?? record.record_type}
                                                </Badge>
                                                {record.is_verified && (
                                                    <Badge variant="outline">{uiText.recordVerifiedBadge}</Badge>
                                                )}
                                            </div>
                                            <p className="mt-2 text-sm font-semibold text-foreground">
                                                {record.title}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {formatDateTime(record.created_at, uiText.locale)}
                                            </p>
                                            {record.content_text && !hasAnalysis(record.analysis_result) && (
                                                <p className="mt-2 text-sm text-muted-foreground">
                                                    {truncateText(record.content_text, 180)}
                                                </p>
                                            )}
                                            <DoctorTestResultSummary doctorComment={record.doctor_comment} language={language} />
                                            <RecordAIAnalysis analysis={record.analysis_result} />
                                        </div>
                                        <div className="flex flex-col gap-2 items-start md:items-end">
                                            {role === "doctor" && (
                                                <div className="flex w-full flex-wrap justify-end gap-2 pb-1">
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        onClick={() => openEditRecord(record)}
                                                    >
                                                        {uiText.editButton}
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="destructive"
                                                        onClick={() => {
                                                            setRecordListError(null)
                                                            setDeleteRecord(record)
                                                        }}
                                                    >
                                                        {uiText.deleteButton}
                                                    </Button>
                                                </div>
                                            )}
                                            {record.file_kind === "image" && record.file_url && (
                                                <button
                                                    type="button"
                                                    onClick={() => setActiveRecord(record)}
                                                    className="rounded-lg border overflow-hidden hover:ring-2 hover:ring-primary/30 transition"
                                                >
                                                    <img
                                                        src={record.file_url}
                                                        alt={record.title}
                                                        className="h-20 w-28 object-cover"
                                                    />
                                                </button>
                                            )}
                                            {record.file_kind === "pdf" && record.file_url && (
                                                <Button size="sm" variant="outline" asChild>
                                                    <a href={record.file_url} target="_blank" rel="noreferrer">
                                                        {uiText.downloadPdf}
                                                    </a>
                                                </Button>
                                            )}
                                            {!record.file_url && (
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <FileText className="h-4 w-4" />
                                                    <span>{uiText.noAttachment}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
            )}

            <Dialog
                open={isRecordUploadDialogOpen}
                onOpenChange={handleRecordUploadDialogOpenChange}
            >
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{language === "vi" ? "Tải tệp y khoa" : "Upload medical files"}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            {language === "vi"
                                ? "Điền thông tin và tải ảnh cận lâm sàng vào kết quả xét nghiệm."
                                : "Fill in details below to add a new clinical image to medical test results."}
                        </p>
                        {selectedCheckupForUpload && (
                            <p className="rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                                {language === "vi"
                                    ? `Tệp này sẽ được liên kết với lần khám: ${formatDateTime(selectedCheckupForUpload.recorded_at, uiText.locale)}.`
                                    : `This file will be linked to check-up at ${formatDateTime(selectedCheckupForUpload.recorded_at, uiText.locale)}.`}
                            </p>
                        )}

                        <div className="grid gap-2">
                            <Label htmlFor="record-type">{uiText.imagingTypeLabel}</Label>
                            <select
                                id="record-type"
                                value={recordType}
                                onChange={(event) => {
                                    setRecordType(event.target.value as ImagingRecordType)
                                    setRecordError(null)
                                }}
                                className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
                            >
                                {imagingTypeOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="record-title">{uiText.recordTitleLabel}</Label>
                            <Input
                                id="record-title"
                                placeholder={uiText.recordTitlePlaceholder}
                                value={recordTitle}
                                onChange={(event) => {
                                    setRecordTitle(event.target.value)
                                }}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="record-image">{uiText.recordFileLabel}</Label>
                            <Input
                                id="record-image"
                                type="file"
                                accept="image/png,image/jpeg,image/jpg,image/bmp,image/tiff"
                                onChange={handleRecordFileChange}
                                ref={recordInputRef}
                            />
                        </div>

                        {recordError && (
                            <p className="text-sm text-destructive">{recordError}</p>
                        )}
                        {recordUploadMutation.isError && (
                            <p className="text-sm text-destructive">
                                {uiText.recordUploadFailed}
                            </p>
                        )}
                    </div>
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => handleRecordUploadDialogOpenChange(false)}
                            disabled={recordUploadMutation.isPending}
                        >
                            {uiText.cancelButton}
                        </Button>
                        <Button
                            type="button"
                            onClick={handleRecordUpload}
                            disabled={!recordFile || recordUploadMutation.isPending}
                        >
                            <Upload className="mr-2 h-4 w-4" />
                            {recordUploadMutation.isPending ? uiText.uploadingLabel : uiText.recordUploadButton}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <UploadProgressOverlay
                open={isUploadProgressOpen}
                title={uiText.uploadProgressTitle}
                stage={uploadProgressStage || getRecordUploadStage(uploadProgressValue, uploadProgressType, uiText)}
                progress={uploadProgressValue}
            />

            <UploadProgressOverlay
                open={isImportProgressOpen}
                title={exportText.importTextButton}
                stage={importProgressStage || exportText.importing}
                progress={importProgressValue}
            />

            <Dialog
                open={isPostUploadDialogOpen}
                onOpenChange={(open) => {
                    setIsPostUploadDialogOpen(open)
                    if (!open) {
                        setPostUploadRecordId(null)
                        setPostUploadLinkedCheckupId(null)
                        setPostUploadTestResultDescription("")
                        setPostUploadFinalConclusion("")
                        setPostUploadComment("")
                        setPostUploadAiAnalysis(null)
                    }
                }}
            >
                <DialogContent className="sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{uiText.postUploadDialogTitle}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            {uiText.postUploadDialogHint}
                        </p>
                        {postUploadAnalysis ? (
                            <RecordAIAnalysis analysis={postUploadAnalysis} />
                        ) : (
                            <div className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
                                {uiText.postUploadNoAnalysis}
                            </div>
                        )}
                        <div className="grid gap-2">
                            <Label htmlFor="post-upload-test-description">
                                {language === "vi" ? "Mô tả kết quả xét nghiệm" : "Doctor's test result description"}
                            </Label>
                            <Textarea
                                id="post-upload-test-description"
                                value={postUploadTestResultDescription}
                                onChange={(event) => setPostUploadTestResultDescription(event.target.value)}
                                rows={3}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="post-upload-final-conclusion">
                                {language === "vi" ? "Kết luận cuối cùng của bác sĩ" : "Doctor's final conclusion"}
                            </Label>
                            <Textarea
                                id="post-upload-final-conclusion"
                                value={postUploadFinalConclusion}
                                onChange={(event) => setPostUploadFinalConclusion(event.target.value)}
                                rows={3}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="post-upload-additional-notes">
                                {language === "vi" ? "Ghi chú thêm (tùy chọn)" : "Additional notes (optional)"}
                            </Label>
                            <Textarea
                                id="post-upload-additional-notes"
                                value={postUploadComment}
                                onChange={(event) => setPostUploadComment(event.target.value)}
                                placeholder={uiText.doctorCommentPlaceholder}
                                rows={3}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setIsPostUploadDialogOpen(false)
                                setPostUploadRecordId(null)
                                setPostUploadLinkedCheckupId(null)
                                setPostUploadTestResultDescription("")
                                setPostUploadFinalConclusion("")
                                setPostUploadComment("")
                                setPostUploadAiAnalysis(null)
                            }}
                        >
                            {uiText.skipButton}
                        </Button>
                        <Button
                            onClick={handlePostUploadCommentSave}
                            disabled={!postUploadRecordId || recordUpdateMutation.isPending}
                        >
                            {recordUpdateMutation.isPending ? uiText.savingLabel : uiText.saveCommentButton}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog
                open={!!editState}
                onOpenChange={(open) => {
                    if (!open) {
                        setEditState(null)
                        setEditError(null)
                    }
                }}
            >
                <DialogContent className="sm:max-w-xl">
                    <DialogHeader>
                        <DialogTitle>{uiText.editDialogTitle}</DialogTitle>
                    </DialogHeader>
                    {editState && (
                        <div className="space-y-4">
                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-title">{uiText.editRecordTitleLabel}</Label>
                                <Input
                                    id="edit-record-title"
                                    value={editState.title}
                                    onChange={(event) =>
                                        setEditState((prev) =>
                                            prev
                                                ? {
                                                    ...prev,
                                                    title: event.target.value,
                                                }
                                                : prev
                                        )
                                    }
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-type">{uiText.editRecordTypeLabel}</Label>
                                <select
                                    id="edit-record-type"
                                    value={editState.recordType}
                                    onChange={(event) =>
                                        setEditState((prev) =>
                                            prev
                                                ? {
                                                    ...prev,
                                                    recordType: event.target.value as RecordEditState["recordType"],
                                                }
                                                : prev
                                        )
                                    }
                                    className="border-input h-9 w-full rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] md:text-sm"
                                >
                                    {recordTypeOptions
                                        .filter((option) => option.value !== "")
                                        .map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                </select>
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-file">{uiText.editRecordFileLabel}</Label>
                                <Input
                                    id="edit-record-file"
                                    type="file"
                                    accept="image/png,image/jpeg,image/jpg,image/bmp,image/tiff,application/pdf"
                                    onChange={handleEditRecordFileChange}
                                />
                                <p className="text-xs text-muted-foreground">
                                    {uiText.editRecordFileHint}
                                </p>
                            </div>

                            <div className="grid gap-2">
                                <Label htmlFor="edit-record-comment">{uiText.editRecordCommentLabel}</Label>
                                <Textarea
                                    id="edit-record-comment"
                                    value={editState.doctorComment}
                                    onChange={(event) =>
                                        setEditState((prev) =>
                                            prev
                                                ? {
                                                    ...prev,
                                                    doctorComment: event.target.value,
                                                }
                                                : prev
                                        )
                                    }
                                    rows={4}
                                    placeholder={uiText.doctorCommentPlaceholder}
                                />
                            </div>

                            {editError && <p className="text-sm text-destructive">{editError}</p>}
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditState(null)}>
                            {uiText.cancelButton}
                        </Button>
                        <Button onClick={handleRecordUpdate} disabled={!editState || recordUpdateMutation.isPending}>
                            {recordUpdateMutation.isPending ? uiText.updatingLabel : uiText.saveChangesButton}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog
                open={!!deleteVital}
                onOpenChange={(open) => {
                    if (!open) {
                        setDeleteVital(null)
                    }
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {language === "vi" ? "Xóa lần khám?" : "Delete check-up?"}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {language === "vi"
                                ? "Bản ghi lần khám và liên kết hiển thị của nó sẽ bị xóa."
                                : "This check-up entry and its linked display context will be removed."}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>{uiText.cancelButton}</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteCheckup}
                            disabled={deleteVitalMutation.isPending}
                        >
                            {deleteVitalMutation.isPending ? uiText.deletingLabel : uiText.deleteButton}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AlertDialog
                open={!!deleteRecord}
                onOpenChange={(open) => {
                    if (!open) {
                        setDeleteRecord(null)
                    }
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{uiText.deleteDialogTitle}</AlertDialogTitle>
                        <AlertDialogDescription>
                            {uiText.deleteDialogDescription}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>{uiText.cancelButton}</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteRecord}
                            disabled={recordDeleteMutation.isPending}
                        >
                            {recordDeleteMutation.isPending ? uiText.deletingLabel : uiText.deleteButton}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <Dialog
                open={!!activeRecord}
                onOpenChange={(open) => {
                    if (!open) {
                        setActiveRecord(null)
                    }
                }}
            >
                <DialogContent className="sm:max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>{activeRecord?.title || uiText.activeRecordFallbackTitle}</DialogTitle>
                    </DialogHeader>
                    {activeRecord?.file_url ? (
                        <div className="space-y-3">
                            <img
                                src={activeRecord.file_url}
                                alt={activeRecord.title}
                                className="w-full rounded-lg border object-contain"
                            />
                            {activeRecord.content_text && !hasAnalysis(activeRecord.analysis_result) && (
                                <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground whitespace-pre-line">
                                    {activeRecord.content_text}
                                </div>
                            )}
                            <DoctorTestResultSummary doctorComment={activeRecord.doctor_comment} language={language} />
                            <RecordAIAnalysis analysis={activeRecord.analysis_result} />
                        </div>
                    ) : (
                        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                            {uiText.activeRecordNoImage}
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    )
}

function getInitials(name: string): string {
    return name
        .split(" ")
        .map(word => word[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
}

function formatDateTime(value: string, locale: string): string {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
        return value
    }
    return date.toLocaleString(locale, {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    })
}

function toDateTimeLocalValue(value: string): string {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return ""
    const timezoneOffsetMs = date.getTimezoneOffset() * 60_000
    return new Date(date.getTime() - timezoneOffsetMs).toISOString().slice(0, 16)
}

type CheckupRecordGroup = {
    vital: VitalSign
    records: MedicalRecord[]
}

function groupMedicalRecordsByCheckup(
    vitals: VitalSign[],
    records: MedicalRecord[]
): {
    groups: CheckupRecordGroup[]
    unlinkedRecords: MedicalRecord[]
} {
    const groups: CheckupRecordGroup[] = vitals.map((vital) => ({ vital, records: [] }))
    const groupIndexByVitalId = new Map(groups.map((group, index) => [group.vital.id, index]))
    if (groups.length === 0) {
        return {
            groups,
            unlinkedRecords: [...records].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
        }
    }

    const linkWindowMs = 72 * 60 * 60 * 1000
    const groupTimes = groups.map((group) => new Date(group.vital.recorded_at).getTime())
    const unlinkedRecords: MedicalRecord[] = []

    for (const record of records) {
        const linkedCheckupId = extractLinkedCheckupIdFromDoctorComment(record.doctor_comment)
        if (linkedCheckupId) {
            const linkedGroupIndex = groupIndexByVitalId.get(linkedCheckupId)
            if (linkedGroupIndex !== undefined) {
                groups[linkedGroupIndex].records.push(record)
                continue
            }
        }

        const recordTime = new Date(record.created_at).getTime()
        if (Number.isNaN(recordTime)) {
            unlinkedRecords.push(record)
            continue
        }

        let nearestIndex = -1
        let nearestDelta = Number.POSITIVE_INFINITY

        for (let index = 0; index < groupTimes.length; index += 1) {
            const vitalTime = groupTimes[index]
            if (Number.isNaN(vitalTime)) continue
            const delta = Math.abs(recordTime - vitalTime)
            if (delta < nearestDelta) {
                nearestDelta = delta
                nearestIndex = index
            }
        }

        if (nearestIndex >= 0 && nearestDelta <= linkWindowMs) {
            groups[nearestIndex].records.push(record)
            continue
        }

        unlinkedRecords.push(record)
    }

    for (const group of groups) {
        group.records.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    }
    unlinkedRecords.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    return { groups, unlinkedRecords }
}

type ParsedTreatmentCheckupNotes = {
    reasonForVisit: string
    testResultComment: string
    patientProgress: string
    treatmentPlan: string
    doctorNotes: string
    plainNotes: string
}

function toTrimmedText(value: unknown): string {
    return typeof value === "string" ? value.trim() : ""
}

function parseTreatmentCheckupNotes(notes: unknown): ParsedTreatmentCheckupNotes {
    const blank: ParsedTreatmentCheckupNotes = {
        reasonForVisit: "",
        testResultComment: "",
        patientProgress: "",
        treatmentPlan: "",
        doctorNotes: "",
        plainNotes: "",
    }
    const raw = toTrimmedText(notes)
    if (!raw) return blank

    try {
        const parsed = JSON.parse(raw)
        if (!parsed || typeof parsed !== "object") {
            return { ...blank, plainNotes: raw }
        }
        const data = parsed as Record<string, unknown>
        const hasStructuredContent = [
            "reason_for_visit",
            "doctor_test_result_comment",
            "patient_progress",
            "treatment_plan",
            "doctor_notes",
            "note_text",
        ].some((key) => toTrimmedText(data[key]))
        if (!hasStructuredContent) {
            return { ...blank, plainNotes: raw }
        }
        return {
            reasonForVisit: toTrimmedText(data.reason_for_visit),
            testResultComment: toTrimmedText(data.doctor_test_result_comment),
            patientProgress: toTrimmedText(data.patient_progress),
            treatmentPlan: toTrimmedText(data.treatment_plan),
            doctorNotes: toTrimmedText(data.doctor_notes),
            plainNotes: toTrimmedText(data.note_text),
        }
    } catch {
        return { ...blank, plainNotes: raw }
    }
}

function buildTreatmentCheckupNotes(form: VitalFormState): string | undefined {
    const reasonForVisit = toTrimmedText(form.reasonForVisit)
    const testResultComment = toTrimmedText(form.testResultComment)
    const patientProgress = toTrimmedText(form.patientProgress)
    const treatmentPlan = toTrimmedText(form.treatmentPlan)
    const doctorNotes = toTrimmedText(form.doctorNotes)
    const plainNotes = toTrimmedText(form.notes)

    const hasStructuredContent = Boolean(
        reasonForVisit || testResultComment || patientProgress || treatmentPlan || doctorNotes
    )
    if (!hasStructuredContent) {
        return plainNotes || undefined
    }

    const payload: Record<string, string> = {
        type: "treatment_checkup",
    }
    if (reasonForVisit) payload.reason_for_visit = reasonForVisit
    if (testResultComment) payload.doctor_test_result_comment = testResultComment
    if (patientProgress) payload.patient_progress = patientProgress
    if (treatmentPlan) payload.treatment_plan = treatmentPlan
    if (doctorNotes) payload.doctor_notes = doctorNotes
    if (plainNotes) payload.note_text = plainNotes

    return JSON.stringify(payload)
}

type ParsedDoctorRecordComment = {
    testResultDescription: string
    finalConclusion: string
    additionalNotes: string
}

function parseDoctorRecordComment(comment: unknown): ParsedDoctorRecordComment {
    const blank: ParsedDoctorRecordComment = {
        testResultDescription: "",
        finalConclusion: "",
        additionalNotes: "",
    }
    const raw = toTrimmedText(comment)
    if (!raw) return blank

    try {
        const parsed = JSON.parse(raw)
        if (parsed && typeof parsed === "object") {
            const data = parsed as Record<string, unknown>
            return {
                testResultDescription:
                    toTrimmedText(data.doctor_test_result_description)
                    || toTrimmedText(data.test_result_description),
                finalConclusion:
                    toTrimmedText(data.doctor_final_conclusion)
                    || toTrimmedText(data.final_conclusion),
                additionalNotes:
                    toTrimmedText(data.doctor_notes)
                    || toTrimmedText(data.note_text),
            }
        }
    } catch {
        // Fallback below for legacy plain-text comments.
    }

    const parts = raw
        .split(/\n{2,}/)
        .map((item) => item.trim())
        .filter(Boolean)

    if (parts.length === 1) {
        return {
            ...blank,
            testResultDescription: parts[0],
        }
    }

    if (parts.length >= 2) {
        return {
            ...blank,
            testResultDescription: parts[0],
            finalConclusion: parts[1],
            additionalNotes: parts.slice(2).join("\n\n"),
        }
    }

    return {
        ...blank,
        testResultDescription: raw,
    }
}

function extractLinkedCheckupIdFromDoctorComment(comment: unknown): string {
    const raw = toTrimmedText(comment)
    if (!raw) return ""

    try {
        const parsed = JSON.parse(raw)
        if (!parsed || typeof parsed !== "object") return ""
        const data = parsed as Record<string, unknown>
        return toTrimmedText(data.linked_checkup_id) || toTrimmedText(data.checkup_id)
    } catch {
        return ""
    }
}

function buildDoctorRecordComment({
    testResultDescription,
    finalConclusion,
    additionalNotes,
}: {
    testResultDescription: string
    finalConclusion: string
    additionalNotes: string
},
linkedCheckupId?: string
): string | undefined {
    const description = toTrimmedText(testResultDescription)
    const conclusion = toTrimmedText(finalConclusion)
    const notes = toTrimmedText(additionalNotes)
    const checkupId = toTrimmedText(linkedCheckupId)

    if (!description && !conclusion && !notes && !checkupId) return undefined
    if (!description && !conclusion && !checkupId) return notes

    const payload: Record<string, string> = {}
    if (description) payload.doctor_test_result_description = description
    if (conclusion) payload.doctor_final_conclusion = conclusion
    if (notes) payload.doctor_notes = notes
    if (checkupId) payload.linked_checkup_id = checkupId
    return JSON.stringify(payload)
}

function DoctorTestResultSummary({
    doctorComment,
    language,
}: {
    doctorComment?: string | null
    language: DashboardLanguage
}) {
    const parsed = parseDoctorRecordComment(doctorComment)
    if (!parsed.testResultDescription && !parsed.finalConclusion && !parsed.additionalNotes) {
        return null
    }

    const labels = language === "vi"
        ? {
            title: "Nhận xét bác sĩ",
            description: "Mô tả kết quả xét nghiệm",
            conclusion: "Kết luận cuối cùng",
            notes: "Ghi chú thêm",
        }
        : {
            title: "Doctor Notes",
            description: "Doctor's test result description",
            conclusion: "Doctor's final conclusion",
            notes: "Additional notes",
        }

    return (
        <div className="mt-3 rounded-lg border bg-background/80 p-3">
            <p className="text-sm font-semibold text-foreground">{labels.title}</p>
            {parsed.testResultDescription && (
                <p className="mt-2 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{labels.description}: </span>
                    {parsed.testResultDescription}
                </p>
            )}
            {parsed.finalConclusion && (
                <p className="mt-2 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{labels.conclusion}: </span>
                    {parsed.finalConclusion}
                </p>
            )}
            {parsed.additionalNotes && (
                <p className="mt-2 text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">{labels.notes}: </span>
                    {parsed.additionalNotes}
                </p>
            )}
        </div>
    )
}

function createEmptyMedicalHistoryFormState(): MedicalHistoryFormState {
    return MEDICAL_HISTORY_KEYS.reduce((accumulator, key) => {
        accumulator[key] = []
        return accumulator
    }, {} as MedicalHistoryFormState)
}

function toHistoryEditorLines(value: unknown): string[] {
    if (!Array.isArray(value)) return []
    return value
        .map((item) => {
            if (typeof item === "string") {
                const trimmed = item.trim()
                if (!trimmed) return ""
                const parsed = parseHistoryJsonString(trimmed)
                return parsed !== null ? stringifyHistoryItem(parsed) : trimmed
            }
            if (item === null || item === undefined) return ""
            if (typeof item === "object") return stringifyHistoryItem(item)
            return String(item).trim()
        })
        .filter(Boolean)
}

function toFlexibleHistoryItems(values: string[]): unknown[] {
    return values
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => parseHistoryDisplayItem(value))
}

function toAllergyHistoryItems(values: string[]): string[] {
    return values
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => {
            const parsed = parseHistoryDisplayItem(value)
            if (typeof parsed === "string") return parsed.trim()
            return stringifyHistoryItem(parsed)
        })
        .filter(Boolean)
}

function toStructuredHistoryItems(
    values: string[],
    primaryKey: "name" | "procedure"
): Array<Record<string, unknown> | string> {
    return values
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => {
            const parsed = parseHistoryDisplayItem(value, primaryKey)
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
                const normalized = { ...(parsed as Record<string, unknown>) }
                const existingPrimaryValue = normalized[primaryKey]
                if (
                    typeof existingPrimaryValue !== "string"
                    || !existingPrimaryValue.trim()
                ) {
                    const alternatePrimaryKey = primaryKey === "name" ? "procedure" : "name"
                    const alternatePrimaryValue = normalized[alternatePrimaryKey]
                    if (typeof alternatePrimaryValue === "string" && alternatePrimaryValue.trim()) {
                        normalized[primaryKey] = alternatePrimaryValue.trim()
                    }
                }
                return normalized
            }
            if (typeof parsed === "string") {
                return { [primaryKey]: parsed }
            }
            return { [primaryKey]: JSON.stringify(parsed) }
        })
}

function buildMedicalHistoryFormState(patient: Patient): MedicalHistoryFormState {
    const medicalHistory = (patient.medical_history && typeof patient.medical_history === "object")
        ? patient.medical_history
        : {}
    const familyHistory = (patient.family_medical_history && typeof patient.family_medical_history === "object")
        ? patient.family_medical_history
        : {}
    const immunization = (patient.immunization_records && typeof patient.immunization_records === "object")
        ? patient.immunization_records
        : {}
    const treatmentHistory = (patient.treatment_history && typeof patient.treatment_history === "object")
        ? patient.treatment_history
        : {}

    const fallbackMedicalHistory = (nestedHistoryArray(familyHistory, "medical_history")
        && typeof nestedHistoryArray(familyHistory, "medical_history") === "object")
        ? (nestedHistoryArray(familyHistory, "medical_history") as Record<string, unknown>)
        : {}
    const fallbackImmunization = (nestedHistoryArray(familyHistory, "immunization_records")
        && typeof nestedHistoryArray(familyHistory, "immunization_records") === "object")
        ? (nestedHistoryArray(familyHistory, "immunization_records") as Record<string, unknown>)
        : {}
    const fallbackTreatmentHistory = (nestedHistoryArray(familyHistory, "treatment_history")
        && typeof nestedHistoryArray(familyHistory, "treatment_history") === "object")
        ? (nestedHistoryArray(familyHistory, "treatment_history") as Record<string, unknown>)
        : {}

    return {
        chronic_conditions: toHistoryEditorLines(
            nestedHistoryArray(medicalHistory, "chronic_conditions") || patient.chronic_conditions
        ),
        past_surgeries: toHistoryEditorLines(
            nestedHistoryArray(medicalHistory, "past_surgeries") || patient.surgical_history
        ),
        hospitalizations: toHistoryEditorLines(
            nestedHistoryArray(medicalHistory, "hospitalizations")
            || nestedHistoryArray(fallbackMedicalHistory, "hospitalizations")
            || nestedHistoryArray(familyHistory, "hospitalizations")
        ),
        medications_history: toHistoryEditorLines(
            nestedHistoryArray(medicalHistory, "medications_history")
            || nestedHistoryArray(fallbackMedicalHistory, "medications_history")
            || nestedHistoryArray(familyHistory, "medications_history")
        ),
        allergies: toHistoryEditorLines(
            nestedHistoryArray(medicalHistory, "allergies") || patient.allergies
        ),
        psychiatric_history: toHistoryEditorLines(
            nestedHistoryArray(medicalHistory, "psychiatric_history")
            || nestedHistoryArray(fallbackMedicalHistory, "psychiatric_history")
            || nestedHistoryArray(familyHistory, "psychiatric_history")
        ),
        family_history_of_chronic_conditions: toHistoryEditorLines(
            nestedHistoryArray(familyHistory, "family_history_of_chronic_conditions")
            || nestedHistoryArray(familyHistory, "chronic_conditions")
        ),
        family_history_of_mental_health_conditions: toHistoryEditorLines(
            nestedHistoryArray(familyHistory, "family_history_of_mental_health_conditions")
        ),
        family_history_of_genetic_conditions: toHistoryEditorLines(
            nestedHistoryArray(familyHistory, "family_history_of_genetic_conditions")
        ),
        vaccines_administered: toHistoryEditorLines(
            nestedHistoryArray(immunization, "vaccines_administered")
            || nestedHistoryArray(fallbackImmunization, "vaccines_administered")
            || nestedHistoryArray(familyHistory, "vaccines_administered")
        ),
        vaccines_due: toHistoryEditorLines(
            nestedHistoryArray(immunization, "vaccines_due")
            || nestedHistoryArray(fallbackImmunization, "vaccines_due")
            || nestedHistoryArray(familyHistory, "vaccines_due")
        ),
        previous_treatments: toHistoryEditorLines(
            nestedHistoryArray(treatmentHistory, "previous_treatments")
            || nestedHistoryArray(fallbackTreatmentHistory, "previous_treatments")
            || nestedHistoryArray(familyHistory, "previous_treatments")
        ),
        physiotherapy: toHistoryEditorLines(
            nestedHistoryArray(treatmentHistory, "physiotherapy")
            || nestedHistoryArray(fallbackTreatmentHistory, "physiotherapy")
            || nestedHistoryArray(familyHistory, "physiotherapy")
        ),
        other_relevant_treatments: toHistoryEditorLines(
            nestedHistoryArray(treatmentHistory, "other_relevant_treatments")
            || nestedHistoryArray(fallbackTreatmentHistory, "other_relevant_treatments")
            || nestedHistoryArray(familyHistory, "other_relevant_treatments")
        ),
    }
}

function buildMedicalHistoryFormStateFromImportPrefill(
    prefill: MedicalHistoryImportPreview
): MedicalHistoryFormState {
    const raw = prefill as Record<MedicalHistoryFieldKey, unknown>
    return MEDICAL_HISTORY_KEYS.reduce((accumulator, key) => {
        accumulator[key] = toHistoryEditorLines(raw[key])
        return accumulator
    }, createEmptyMedicalHistoryFormState())
}

function buildMedicalHistoryUpdatePayload(
    form: MedicalHistoryFormState,
    patient: Patient
): PatientUpdateInput {
    const chronicConditions = toStructuredHistoryItems(form.chronic_conditions, "name")
    const pastSurgeries = toStructuredHistoryItems(form.past_surgeries, "procedure")
    const hospitalizations = toFlexibleHistoryItems(form.hospitalizations)
    const medicationsHistory = toFlexibleHistoryItems(form.medications_history)
    const allergies = toAllergyHistoryItems(form.allergies)
    const psychiatricHistory = toFlexibleHistoryItems(form.psychiatric_history)
    const familyHistoryOfChronicConditions = toFlexibleHistoryItems(form.family_history_of_chronic_conditions)
    const familyHistoryOfMentalHealthConditions = toFlexibleHistoryItems(form.family_history_of_mental_health_conditions)
    const familyHistoryOfGeneticConditions = toFlexibleHistoryItems(form.family_history_of_genetic_conditions)
    const vaccinesAdministered = toFlexibleHistoryItems(form.vaccines_administered)
    const vaccinesDue = toFlexibleHistoryItems(form.vaccines_due)
    const previousTreatments = toFlexibleHistoryItems(form.previous_treatments)
    const physiotherapy = toFlexibleHistoryItems(form.physiotherapy)
    const otherRelevantTreatments = toFlexibleHistoryItems(form.other_relevant_treatments)

    const familyHistoryBase = (patient.family_medical_history && typeof patient.family_medical_history === "object")
        ? { ...(patient.family_medical_history as Record<string, unknown>) }
        : {}

    const familyHistoryPayload: Record<string, unknown> = {
        ...familyHistoryBase,
        family_history_of_chronic_conditions: familyHistoryOfChronicConditions,
        family_history_of_mental_health_conditions: familyHistoryOfMentalHealthConditions,
        family_history_of_genetic_conditions: familyHistoryOfGeneticConditions,
        hospitalizations,
        medications_history: medicationsHistory,
        psychiatric_history: psychiatricHistory,
        vaccines_administered: vaccinesAdministered,
        vaccines_due: vaccinesDue,
        previous_treatments: previousTreatments,
        physiotherapy,
        other_relevant_treatments: otherRelevantTreatments,
    }

    return {
        chronic_conditions: chronicConditions,
        surgical_history: pastSurgeries,
        allergies,
        family_medical_history: familyHistoryPayload,
        medical_history: {
            chronic_conditions: chronicConditions,
            past_surgeries: pastSurgeries,
            hospitalizations,
            medications_history: medicationsHistory,
            allergies,
            psychiatric_history: psychiatricHistory,
        },
        immunization_records: {
            vaccines_administered: vaccinesAdministered,
            vaccines_due: vaccinesDue,
        },
        treatment_history: {
            previous_treatments: previousTreatments,
            physiotherapy,
            other_relevant_treatments: otherRelevantTreatments,
        },
    }
}

type HistorySection = {
    title: string
    items: string[]
}

function stringifyHistoryItem(value: unknown): string {
    if (typeof value === "string") {
        const trimmed = value.trim()
        if (!trimmed) return ""
        const parsedJson = parseHistoryJsonString(trimmed)
        if (parsedJson !== null) {
            return stringifyHistoryItem(parsedJson)
        }
        return trimmed
    }
    if (Array.isArray(value)) {
        return value
            .map((item) => stringifyHistoryItem(item))
            .filter(Boolean)
            .join(", ")
    }
    if (value && typeof value === "object") {
        return formatHistoryObject(value as Record<string, unknown>)
    }
    if (value === null || value === undefined) return ""
    return String(value).trim()
}

function toHistoryItems(value: unknown): string[] {
    if (Array.isArray(value)) {
        return value
            .map((item) => stringifyHistoryItem(item))
            .filter(Boolean)
    }
    const item = stringifyHistoryItem(value)
    return item ? [item] : []
}

function parseHistoryJsonString(value: string): unknown | null {
    if (!value) return null
    const firstChar = value[0]
    if (firstChar !== "{" && firstChar !== "[") return null
    try {
        return JSON.parse(value)
    } catch {
        return null
    }
}

function parseHistoryDisplayItem(
    value: string,
    preferredPrimaryKey?: "name" | "procedure"
): unknown {
    const parsedJson = parseHistoryJsonString(value)
    if (parsedJson !== null) return parsedJson

    const trimmed = value.trim()
    if (!trimmed) return ""

    const parenthesizedMatch = trimmed.match(/^(.*?)\s*\((.+)\)$/)
    if (parenthesizedMatch) {
        const primary = parenthesizedMatch[1].trim()
        const details = parseHistoryDetailsText(parenthesizedMatch[2] || "")
        if (Object.keys(details).length > 0) {
            const primaryKey = preferredPrimaryKey ?? "name"
            const result: Record<string, unknown> = { ...details }
            if (primary) result[primaryKey] = primary
            return result
        }
    }

    const inlineDetails = parseHistoryDetailsText(trimmed)
    const detailParts = trimmed.split(/\s+\|\s+/)
    if (detailParts.length > 1 && Object.keys(inlineDetails).length > 0) {
        return inlineDetails
    }

    return trimmed
}

function parseHistoryDetailsText(text: string): Record<string, unknown> {
    const details: Record<string, unknown> = {}
    const parts = text
        .split(/\s+\|\s+/)
        .map((part) => part.trim())
        .filter(Boolean)

    for (const part of parts) {
        const separatorIndex = part.indexOf(":")
        if (separatorIndex <= 0) continue

        const label = part.slice(0, separatorIndex).trim()
        const rawValue = part.slice(separatorIndex + 1).trim()
        if (!label || !rawValue) continue

        const key = historyLabelToKey(label)
        const parsedValue = parseHistoryJsonString(rawValue)
        details[key] = parsedValue !== null ? parsedValue : rawValue
    }

    return details
}

function historyLabelToKey(label: string): string {
    const normalized = label.trim().toLowerCase()
    const mapping: Record<string, string> = {
        diagnosed: "diagnosed_date",
        "icd-10": "icd10_code",
        date: "date",
        timeline: "timeline",
        stage: "stage",
        status: "status",
        outcome: "outcome",
        reaction: "reaction",
        reason: "reason",
        dosage: "dosage",
        frequency: "frequency",
        notes: "notes",
    }
    if (mapping[normalized]) return mapping[normalized]

    return label
        .trim()
        .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
        .replace(/[^a-zA-Z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "")
        .toLowerCase()
}

function formatHistoryObject(record: Record<string, unknown>): string {
    const preferredPrimaryKeys = [
        "name",
        "procedure",
        "condition",
        "diagnosis",
        "treatment",
        "medication",
        "vaccine",
        "allergy",
        "hospital",
        "facility",
    ]
    const preferredDetailKeys = [
        "diagnosed_date",
        "date",
        "timeline",
        "stage",
        "status",
        "outcome",
        "reaction",
        "reason",
        "icd10_code",
        "dosage",
        "frequency",
        "notes",
    ]

    let primaryKey: string | null = null
    let primaryValue = ""
    for (const key of preferredPrimaryKeys) {
        const text = stringifyHistoryItem(record[key])
        if (text) {
            primaryKey = key
            primaryValue = text
            break
        }
    }

    const detailKeys = [
        ...preferredDetailKeys.filter((key) => key in record && key !== primaryKey),
        ...Object.keys(record).filter((key) => !preferredDetailKeys.includes(key) && key !== primaryKey),
    ]

    const details = detailKeys
        .map((key) => {
            const text = stringifyHistoryItem(record[key])
            if (!text) return ""
            return `${formatHistoryFieldLabel(key)}: ${text}`
        })
        .filter(Boolean)

    if (primaryValue && details.length === 0) return primaryValue
    if (primaryValue && details.length > 0) return `${primaryValue} (${details.join(" | ")})`
    return details.join(" | ")
}

function formatHistoryFieldLabel(key: string): string {
    const labels: Record<string, string> = {
        diagnosed_date: "Diagnosed",
        icd10_code: "ICD-10",
        date: "Date",
        timeline: "Timeline",
        stage: "Stage",
        status: "Status",
        outcome: "Outcome",
        reaction: "Reaction",
        reason: "Reason",
        dosage: "Dosage",
        frequency: "Frequency",
        notes: "Notes",
    }
    if (labels[key]) return labels[key]
    const normalized = key.replace(/_/g, " ").trim()
    if (!normalized) return key
    return normalized.replace(/\b\w/g, (char) => char.toUpperCase())
}

function nestedHistoryArray(source: unknown, key: string): unknown {
    if (!source || typeof source !== "object") return undefined
    return (source as Record<string, unknown>)[key]
}

function buildPatientHistorySections(patient: Patient, language: DashboardLanguage): HistorySection[] {
    const medicalHistory = (patient.medical_history && typeof patient.medical_history === "object")
        ? patient.medical_history
        : {}
    const familyHistory = (patient.family_medical_history && typeof patient.family_medical_history === "object")
        ? patient.family_medical_history
        : {}
    const immunization = (patient.immunization_records && typeof patient.immunization_records === "object")
        ? patient.immunization_records
        : {}
    const treatmentHistory = (patient.treatment_history && typeof patient.treatment_history === "object")
        ? patient.treatment_history
        : {}

    const isVi = language === "vi"
    const sections: HistorySection[] = [
        {
            title: isVi ? "Bệnh mạn tính" : "Chronic Conditions",
            items: toHistoryItems(nestedHistoryArray(medicalHistory, "chronic_conditions") || patient.chronic_conditions),
        },
        {
            title: isVi ? "Phẫu thuật trước đây" : "Past Surgeries",
            items: toHistoryItems(nestedHistoryArray(medicalHistory, "past_surgeries") || patient.surgical_history),
        },
        {
            title: isVi ? "Tiền sử nhập viện" : "Hospitalizations",
            items: toHistoryItems(
                nestedHistoryArray(medicalHistory, "hospitalizations")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "medical_history"), "hospitalizations")
                || nestedHistoryArray(familyHistory, "hospitalizations")
            ),
        },
        {
            title: isVi ? "Tiền sử dùng thuốc" : "Medications History",
            items: toHistoryItems(
                nestedHistoryArray(medicalHistory, "medications_history")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "medical_history"), "medications_history")
                || nestedHistoryArray(familyHistory, "medications_history")
            ),
        },
        {
            title: isVi ? "Dị ứng" : "Allergies",
            items: toHistoryItems(nestedHistoryArray(medicalHistory, "allergies") || patient.allergies),
        },
        {
            title: isVi ? "Tiền sử tâm thần" : "Psychiatric History",
            items: toHistoryItems(
                nestedHistoryArray(medicalHistory, "psychiatric_history")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "medical_history"), "psychiatric_history")
                || nestedHistoryArray(familyHistory, "psychiatric_history")
            ),
        },
        {
            title: isVi ? "Tiền sử gia đình - bệnh mạn tính" : "Family History of Chronic Conditions",
            items: toHistoryItems(
                nestedHistoryArray(familyHistory, "family_history_of_chronic_conditions")
                || nestedHistoryArray(familyHistory, "chronic_conditions")
            ),
        },
        {
            title: isVi ? "Tiền sử gia đình - sức khỏe tâm thần" : "Family History of Mental Health Conditions",
            items: toHistoryItems(nestedHistoryArray(familyHistory, "family_history_of_mental_health_conditions")),
        },
        {
            title: isVi ? "Tiền sử gia đình - bệnh di truyền" : "Family History of Genetic Conditions",
            items: toHistoryItems(nestedHistoryArray(familyHistory, "family_history_of_genetic_conditions")),
        },
        {
            title: isVi ? "Vaccine đã tiêm" : "Vaccines Administered",
            items: toHistoryItems(
                nestedHistoryArray(immunization, "vaccines_administered")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "immunization_records"), "vaccines_administered")
                || nestedHistoryArray(familyHistory, "vaccines_administered")
            ),
        },
        {
            title: isVi ? "Vaccine cần tiêm" : "Vaccines Due",
            items: toHistoryItems(
                nestedHistoryArray(immunization, "vaccines_due")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "immunization_records"), "vaccines_due")
                || nestedHistoryArray(familyHistory, "vaccines_due")
            ),
        },
        {
            title: isVi ? "Điều trị trước đây" : "Previous Treatments",
            items: toHistoryItems(
                nestedHistoryArray(treatmentHistory, "previous_treatments")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "treatment_history"), "previous_treatments")
                || nestedHistoryArray(familyHistory, "previous_treatments")
            ),
        },
        {
            title: isVi ? "Vật lý trị liệu" : "Physiotherapy",
            items: toHistoryItems(
                nestedHistoryArray(treatmentHistory, "physiotherapy")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "treatment_history"), "physiotherapy")
                || nestedHistoryArray(familyHistory, "physiotherapy")
            ),
        },
        {
            title: isVi ? "Điều trị liên quan khác" : "Other Relevant Treatments",
            items: toHistoryItems(
                nestedHistoryArray(treatmentHistory, "other_relevant_treatments")
                || nestedHistoryArray(nestedHistoryArray(familyHistory, "treatment_history"), "other_relevant_treatments")
                || nestedHistoryArray(familyHistory, "other_relevant_treatments")
            ),
        },
    ]

    return sections.filter((section) => section.items.length > 0)
}

function formatVitalMetrics(vital: VitalSign, uiText: PatientDetailUiText): string[] {
    const metrics: string[] = []

    if (vital.blood_pressure_systolic || vital.blood_pressure_diastolic) {
        const systolic = vital.blood_pressure_systolic ?? "--"
        const diastolic = vital.blood_pressure_diastolic ?? "--"
        metrics.push(`${uiText.metrics.bloodPressure} ${systolic}/${diastolic} mmHg`)
    }
    if (vital.heart_rate) {
        metrics.push(`${uiText.metrics.heartRate} ${vital.heart_rate} bpm`)
    }
    if (vital.blood_glucose) {
        const timingLabel = formatGlucoseTiming(vital.blood_glucose_timing, uiText)
        metrics.push(`${uiText.metrics.bloodGlucose} ${vital.blood_glucose} mmol/L${timingLabel ? ` (${timingLabel})` : ""}`)
    }
    if (vital.temperature) {
        metrics.push(`${uiText.metrics.temperature} ${vital.temperature} °C`)
    }
    if (vital.oxygen_saturation) {
        metrics.push(`${uiText.metrics.oxygenSaturation} ${vital.oxygen_saturation}%`)
    }
    if (vital.weight_kg) {
        metrics.push(`${uiText.metrics.weight} ${vital.weight_kg} kg`)
    }

    return metrics
}

function formatVitalSource(source: VitalSign["source"] | undefined, uiText: PatientDetailUiText): string {
    if (!source) return uiText.options.vitalSource.unknown
    return uiText.options.vitalSource[source] ?? uiText.options.vitalSource.unknown
}

function normalizeClinicalSummaryMarkdown(summary: string | null): string {
    const raw = String(summary || "")
        .replace(/\r\n/g, "\n")
        .replace(/\r/g, "\n")
        .trim()
    if (!raw) return ""

    const sectionPatterns = [
        {
            pattern: "Danh sách vấn đề(?:\\s*\\(Problem List\\))?|Problem List",
            header: "Danh sách vấn đề (Problem List)",
        },
        {
            pattern: "Thuốc đang dùng(?:\\s*\\(Current Medications\\))?|Current Medications",
            header: "Thuốc đang dùng (Current Medications)",
        },
        {
            pattern: "Dị ứng(?:\\s*\\(Allergies\\))?|Allergies",
            header: "Dị ứng (Allergies)",
        },
        {
            pattern: "Diễn tiến bệnh(?:\\s*\\(Disease Progress\\))?|Disease Progress",
            header: "Diễn tiến bệnh (Disease Progress)",
        },
        {
            pattern: "Tóm tắt sinh hiệu gần nhất(?:\\s*\\(Recent Vitals\\))?|Recent Vitals",
            header: "Tóm tắt sinh hiệu gần nhất (Recent Vitals)",
        },
        {
            pattern: "Đánh giá lâm sàng(?:\\s*\\(Clinical Assessment\\))?|Clinical Assessment",
            header: "Đánh giá lâm sàng (Clinical Assessment)",
        },
    ]

    let text = raw.replace(/\u00a0/g, " ").replace(/[ \t]+/g, " ")
    const sectionPrefixes = sectionPatterns.map(({ header }) => header.split("(")[0].trim().toLowerCase())

    // Drop malformed headings like "## Danh sách vấn đề (undefined" and orphan ")" lines.
    text = text
        .split("\n")
        .filter((line) => {
            const trimmed = line.trim()
            if (!trimmed) return true
            if (/^[()]+$/.test(trimmed)) return false
            if (!/\bundefined\b/i.test(trimmed)) return true

            const headingText = trimmed
                .replace(/^#{1,6}\s*/, "")
                .replace(/^\*\*|\*\*$/g, "")
                .trim()
                .toLowerCase()

            const looksLikeSectionHeader = sectionPrefixes.some(prefix => headingText.startsWith(prefix))
            return !looksLikeSectionHeader
        })
        .join("\n")

    text = text
        .split("\n")
        .map((line) => {
            const boldMarkers = (line.match(/\*\*/g) || []).length
            const balanced = boldMarkers % 2 === 0 ? line : line.replace(/\*\*/g, "")
            return balanced.replace(/(?!^)(\d+[.)]\s*(?=[\[\]A-Za-zÀ-ỹ]))/g, "\n$1")
        })
        .join("\n")

    text = text.replace(/([.!?])(?=[A-Za-zÀ-ỹ#*])/g, "$1 ")

    for (const section of sectionPatterns) {
        const matcher = new RegExp(
            `(^|[\\n.!?])\\s*(?:#{1,4}\\s*)?(?:\\*\\*)?\\s*(?:${section.pattern})\\s*(?:\\*\\*)?\\s*:?\\s*`,
            "gi"
        )
        text = text.replace(matcher, (_match, prefix: string) => `${prefix}\n\n## ${section.header}\n`)
    }

    text = text.replace(/([^\n]|^)(##\s)/g, (_match, prefix: string, header: string) => `${prefix}\n\n${header}`)
    text = text.replace(/(##[^\n]+)\s*(?=(?:\d+[.)]|[-•*]))/g, "$1\n")
    text = text.replace(/(^|[^A-Za-zÀ-ỹ0-9])(\d+[.)])(?=\S)/g, "$1$2 ")
    text = text.replace(/([:;.!?\n])\s*\*(?=[A-Za-zÀ-ỹ0-9])/g, "$1\n- ")
    text = text.replace(/([:;.!?\n])\s*[•●▪]\s*(?=[A-Za-zÀ-ỹ0-9])/g, "$1\n- ")
    text = text.replace(/([:;.!?])\s*-\s+(?=[A-Za-zÀ-ỹ0-9])/g, "$1\n- ")

    // Defensive de-duplication in case malformed input triggers repeated canonical headings.
    const canonicalSectionTitles = new Set(
        sectionPatterns.map(({ header }) => header.replace(/\s+/g, " ").trim().toLowerCase())
    )
    const dedupedLines: string[] = []
    const seenHeaders = new Set<string>()
    for (const line of text.split("\n")) {
        const trimmed = line.trim()
        if (/^[()]+$/.test(trimmed)) continue
        if (/^##\s+/.test(trimmed)) {
            const normalizedTitle = trimmed
                .replace(/^##\s+/, "")
                .replace(/\s*:+\s*$/, "")
                .replace(/\s+/g, " ")
                .trim()
                .toLowerCase()
            if (canonicalSectionTitles.has(normalizedTitle)) {
                if (seenHeaders.has(normalizedTitle)) continue
                seenHeaders.add(normalizedTitle)
            }
            dedupedLines.push(line)
            continue
        }
        dedupedLines.push(line)
    }

    text = dedupedLines.join("\n")

    return text.replace(/\n{3,}/g, "\n\n").trim()
}

function formatGlucoseTiming(
    timing: VitalSign["blood_glucose_timing"] | undefined,
    uiText: PatientDetailUiText
): string {
    if (!timing) return ""
    return uiText.options.glucoseTiming[timing] ?? ""
}

function formatVitalNotes(notes: string): string {
    const trimmed = notes.trim()
    if (!trimmed) return ""

    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        try {
            JSON.parse(trimmed)
            return "" // Hide raw JSON payload completely
        } catch {
            return notes
        }
    }

    return notes
}

function truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text
    return `${text.slice(0, maxLength)}...`
}

function hasAnalysis(value: unknown): boolean {
    if (!value) return false
    if (typeof value === "string") return value.trim().length > 0
    if (typeof value === "object") return true
    return false
}

function getErrorMessage(error: unknown, fallback: string): string {
    if (error && typeof error === "object" && "message" in error) {
        const message = String((error as { message?: unknown }).message || "").trim()
        if (message) return message
    }
    return fallback
}

function triggerFileDownload(blob: Blob, fileName: string): void {
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = objectUrl
    anchor.download = fileName
    anchor.rel = "noopener"
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

function buildDownloadName(name: string | undefined, fallback: string, suffix = ""): string {
    const candidate = String(name || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")

    if (!candidate) {
        return fallback
    }

    const extension = fallback.includes(".") ? fallback.slice(fallback.lastIndexOf(".")) : ""
    if (!extension) {
        return candidate
    }

    return `${candidate}${suffix}${extension}`
}
