import { useState } from 'react';
import { Upload, FileText, Image as ImageIcon, File, X, CheckCircle2, Loader2 } from 'lucide-react';

interface DocumentUploadProps {
  patientId: string;
}

interface UploadedFile {
  id: string;
  name: string;
  type: 'medical-record' | 'lab-result' | 'imaging' | 'ecg' | 'prescription';
  size: string;
  uploadedAt: Date;
  status: 'uploading' | 'processing' | 'completed';
  aiSummary?: string;
}

export function DocumentUpload({ patientId }: DocumentUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const documentTypes = [
    { value: 'medical-record', label: 'Bệnh án / Giấy ra viện', icon: FileText },
    { value: 'lab-result', label: 'Kết quả xét nghiệm', icon: FileText },
    { value: 'imaging', label: 'CT / X-quang / Siêu âm', icon: ImageIcon },
    { value: 'ecg', label: 'Điện tâm đồ', icon: File },
    { value: 'prescription', label: 'Đơn thuốc', icon: FileText },
  ];

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (fileList: File[]) => {
    const newFiles: UploadedFile[] = fileList.map(file => ({
      id: Date.now().toString() + Math.random(),
      name: file.name,
      type: 'medical-record',
      size: formatFileSize(file.size),
      uploadedAt: new Date(),
      status: 'uploading',
    }));

    setFiles(prev => [...prev, ...newFiles]);

    // Simulate upload and processing
    newFiles.forEach((file, idx) => {
      setTimeout(() => {
        setFiles(prev =>
          prev.map(f => (f.id === file.id ? { ...f, status: 'processing' } : f))
        );

        setTimeout(() => {
          const aiSummaries = [
            'Phát hiện: Huyết áp 165/98 mmHg, đường huyết 152 mg/dL. Đề xuất điều chỉnh thuốc hạ áp và kiểm soát đường huyết.',
            'Kết quả xét nghiệm cho thấy HbA1c 8.1% (cao), Cholesterol 258 mg/dL (cao). Khuyến nghị thêm statin và tăng cường kiểm soát đường huyết.',
            'Hình ảnh X-quang ngực bình thường, không có dấu hiệu nhiễm trùng hoặc tràn dịch. Tim phổi trong giới hạn bình thường.',
            'ECG cho thấy nhịp xoang, tần số 76 bpm. Có ST chênh xuống nhẹ ở V4-V6, cần theo dõi thêm về thiếu máu cơ tim.',
            'Đơn thuốc bao gồm: Amlodipine 10mg, Metformin 850mg x2, Atorvastatin 20mg. Lưu ý kiểm tra chức năng gan định kỳ.',
          ];

          setFiles(prev =>
            prev.map(f =>
              f.id === file.id
                ? {
                    ...f,
                    status: 'completed',
                    aiSummary: aiSummaries[idx % aiSummaries.length],
                  }
                : f
            )
          );
        }, 2000);
      }, 1500);
    });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Tải lên tài liệu y tế</h3>
          <p className="text-gray-600">
            Tài liệu sẽ được AI tự động phân tích và tạo tóm tắt để hỗ trợ theo dõi bệnh án
          </p>
        </div>

        {/* Document Type Selection */}
        <div className="bg-white/70 backdrop-blur-xl rounded-xl shadow-lg border border-purple-200/50 p-6">
          <h4 className="font-semibold text-gray-900 mb-3">Loại tài liệu</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {documentTypes.map(type => {
              const Icon = type.icon;
              return (
                <button
                  key={type.value}
                  className="flex items-center gap-3 p-3 border-2 border-purple-200/50 rounded-lg hover:border-purple-400 hover:bg-purple-50/50 transition-colors text-left backdrop-blur-sm"
                >
                  <Icon className="w-5 h-5 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">{type.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Upload Zone */}
        <div
          className={`bg-white/70 backdrop-blur-xl rounded-xl shadow-lg border-2 border-dashed transition-colors ${
            dragActive ? 'border-purple-500 bg-purple-50/50' : 'border-purple-300/50'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <label className="flex flex-col items-center justify-center p-12 cursor-pointer">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-100 to-violet-100 rounded-full flex items-center justify-center mb-4 shadow-md">
              <Upload className="w-8 h-8 text-purple-600" />
            </div>
            <h4 className="font-semibold text-gray-900 mb-2">
              Kéo thả tệp vào đây hoặc nhấn để chọn
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              Hỗ trợ: PDF, JPG, PNG, DICOM (tối đa 10MB)
            </p>
            <input
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.dcm"
              onChange={handleFileInput}
              className="hidden"
            />
            <button className="px-6 py-2 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg hover:from-purple-700 hover:to-violet-700 transition-all shadow-md">
              Chọn tệp
            </button>
          </label>
        </div>

        {/* Uploaded Files */}
        {files.length > 0 && (
          <div className="bg-white/70 backdrop-blur-xl rounded-xl shadow-lg border border-purple-200/50 p-6">
            <h4 className="font-semibold text-gray-900 mb-4">
              Tệp đã tải lên ({files.length})
            </h4>
            <div className="space-y-3">
              {files.map(file => (
                <div
                  key={file.id}
                  className="flex items-start gap-4 p-4 bg-white/60 backdrop-blur-sm rounded-lg border border-purple-200/30 shadow-sm"
                >
                  <div className="flex-shrink-0">
                    {file.status === 'completed' ? (
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-green-600" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h5 className="font-semibold text-gray-900 truncate">{file.name}</h5>
                      <button
                        onClick={() => removeFile(file.id)}
                        className="flex-shrink-0 text-gray-400 hover:text-red-600 transition-colors"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
                      <span>{file.size}</span>
                      <span>•</span>
                      <span>{file.uploadedAt.toLocaleTimeString('vi-VN')}</span>
                    </div>

                    {file.status === 'uploading' && (
                      <div className="flex items-center gap-2 text-sm text-blue-600">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Đang tải lên...</span>
                      </div>
                    )}

                    {file.status === 'processing' && (
                      <div className="flex items-center gap-2 text-sm text-blue-600">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>AI đang phân tích...</span>
                      </div>
                    )}

                    {file.status === 'completed' && file.aiSummary && (
                      <div className="mt-2 p-3 bg-purple-50/80 backdrop-blur-sm border border-purple-200/50 rounded-lg shadow-sm">
                        <div className="flex items-start gap-2">
                          <div className="flex-shrink-0 w-5 h-5 bg-gradient-to-br from-purple-600 to-violet-600 rounded flex items-center justify-center mt-0.5 shadow-sm">
                            <span className="text-xs text-white font-bold">AI</span>
                          </div>
                          <div>
                            <div className="text-xs font-semibold text-purple-900 mb-1">
                              Tóm tắt tự động:
                            </div>
                            <p className="text-sm text-purple-800">{file.aiSummary}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-purple-50/80 backdrop-blur-sm border border-purple-200/50 rounded-xl p-4 shadow-md">
          <h5 className="font-semibold text-purple-900 mb-2">🤖 AI tự động xử lý</h5>
          <ul className="space-y-1 text-sm text-purple-800">
            <li>• Nhận dạng văn bản từ tài liệu scan (OCR)</li>
            <li>• Trích xuất thông tin quan trọng: chẩn đoán, thuốc, xét nghiệm</li>
            <li>• Phát hiện các chỉ số bất thường và nguy cơ</li>
            <li>• Gắn thẻ thời gian và lưu vào hồ sơ bệnh án</li>
            <li>• Tạo cảnh báo nếu phát hiện giá trị nguy hiểm</li>
          </ul>
        </div>
      </div>
    </div>
  );
}