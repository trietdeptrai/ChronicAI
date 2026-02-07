import { Alert } from '@/lib/data/mockData';
import { AlertTriangle, Info, X } from 'lucide-react';

interface AlertPanelProps {
  alerts: Alert[];
  onClose: () => void;
  onAlertClick?: (patientId: string) => void;
}

export function AlertPanel({ alerts, onClose, onAlertClick }: AlertPanelProps) {
  const getSeverityIcon = (severity: Alert['severity']) => {
    if (severity === 'critical') return <AlertTriangle className="w-5 h-5 text-red-600" />;
    if (severity === 'warning') return <AlertTriangle className="w-5 h-5 text-orange-600" />;
    return <Info className="w-5 h-5 text-blue-600" />;
  };

  const getSeverityColor = (severity: Alert['severity']) => {
    if (severity === 'critical') return 'bg-red-50 border-red-200';
    if (severity === 'warning') return 'bg-orange-50 border-orange-200';
    return 'bg-blue-50 border-blue-200';
  };

  const getSeverityTextColor = (severity: Alert['severity']) => {
    if (severity === 'critical') return 'text-red-900';
    if (severity === 'warning') return 'text-orange-900';
    return 'text-blue-900';
  };

  const unreadAlerts = alerts.filter(a => !a.read);
  const readAlerts = alerts.filter(a => a.read);

  return (
    <div className="bg-white/70 backdrop-blur-md rounded-2xl shadow-lg border border-white/40 max-h-[80vh] flex flex-col">
      <div className="p-4 border-b border-gray-200/30 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-gray-900">Thông báo</h3>
          {unreadAlerts.length > 0 && (
            <p className="text-sm text-gray-600">{unreadAlerts.length} thông báo mới</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {unreadAlerts.length > 0 && (
          <>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Chưa đọc
            </div>
            {unreadAlerts.map(alert => (
              <div
                key={alert.id}
                className={`p-3 rounded-xl border backdrop-blur-sm ${getSeverityColor(alert.severity)} ${onAlertClick ? 'cursor-pointer hover:shadow-md transition-all' : ''}`}
                onClick={() => {
                  if (onAlertClick) {
                    onAlertClick(alert.patientId);
                    onClose();
                  }
                }}
              >
                <div className="flex items-start gap-3">
                  {getSeverityIcon(alert.severity)}
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${getSeverityTextColor(alert.severity)} font-medium mb-1`}>
                      {alert.message}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(alert.date).toLocaleString('vi-VN')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {readAlerts.length > 0 && (
          <>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-4">
              Đã đọc
            </div>
            {readAlerts.map(alert => (
              <div
                key={alert.id}
                className={`p-3 rounded-xl border border-gray-200/50 bg-gray-50/50 backdrop-blur-sm opacity-60 ${onAlertClick ? 'cursor-pointer hover:opacity-80 hover:shadow-md transition-all' : ''}`}
                onClick={() => {
                  if (onAlertClick) {
                    onAlertClick(alert.patientId);
                    onClose();
                  }
                }}
              >
                <div className="flex items-start gap-3">
                  {getSeverityIcon(alert.severity)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700 mb-1">{alert.message}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(alert.date).toLocaleString('vi-VN')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {alerts.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Info className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>Không có thông báo</p>
          </div>
        )}
      </div>
    </div>
  );
}