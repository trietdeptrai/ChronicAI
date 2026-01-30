import { useState } from 'react';
import { Calendar as CalendarIcon, Clock, CheckCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { Appointment, timeSlots, appointmentTypes, mockAppointments } from '@/data/appointmentData';
import { format, addDays, startOfWeek, isSameDay } from 'date-fns';
import { vi } from 'date-fns/locale';

interface AppointmentBookingProps {
  patientId: string;
  patientName: string;
}

export function AppointmentBooking({ patientId, patientName }: AppointmentBookingProps) {
  const [currentWeek, setCurrentWeek] = useState(startOfWeek(new Date(), { locale: vi }));
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>('followup');
  const [notes, setNotes] = useState('');
  const [isBooked, setIsBooked] = useState(false);

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeek, i));

  const nextWeek = () => setCurrentWeek(addDays(currentWeek, 7));
  const prevWeek = () => setCurrentWeek(addDays(currentWeek, -7));

  const isTimeSlotAvailable = (date: Date, time: string) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    const existingAppointment = mockAppointments.find(
      apt => apt.date === dateStr && apt.time === time && apt.status === 'scheduled'
    );
    return !existingAppointment;
  };

  const getAvailableSlots = (date: Date) => {
    return timeSlots.filter(time => isTimeSlotAvailable(date, time));
  };

  const handleBooking = () => {
    if (selectedDate && selectedTime && selectedType) {
      // In a real app, this would make an API call
      console.log('Booking appointment:', {
        patientId,
        patientName,
        date: format(selectedDate, 'yyyy-MM-dd'),
        time: selectedTime,
        type: selectedType,
        notes
      });
      setIsBooked(true);
      
      // Reset after 3 seconds
      setTimeout(() => {
        setIsBooked(false);
        setSelectedDate(null);
        setSelectedTime(null);
        setNotes('');
      }, 3000);
    }
  };

  if (isBooked) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
            <CheckCircle className="w-10 h-10 text-white" />
          </div>
          <h3 className="text-2xl font-bold text-gray-800 mb-2">Đặt lịch thành công!</h3>
          <p className="text-gray-600 mb-1">
            {selectedDate && format(selectedDate, 'EEEE, d MMMM yyyy', { locale: vi })}
          </p>
          <p className="text-gray-600">Lúc {selectedTime}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 border-b border-gray-200/30">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Đặt lịch khám</h2>
        <p className="text-gray-600">Chọn ngày và giờ phù hợp với bạn</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Week Selector */}
        <div className="bg-white/40 backdrop-blur-sm rounded-2xl p-4 border border-white/40">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Chọn ngày</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={prevWeek}
                className="p-2 hover:bg-white/40 rounded-xl transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-gray-600" />
              </button>
              <span className="text-sm text-gray-600 min-w-[120px] text-center">
                {format(weekDays[0], 'd MMM', { locale: vi })} - {format(weekDays[6], 'd MMM', { locale: vi })}
              </span>
              <button
                onClick={nextWeek}
                className="p-2 hover:bg-white/40 rounded-xl transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-2">
            {weekDays.map((day, idx) => {
              const isToday = isSameDay(day, new Date());
              const isSelected = selectedDate && isSameDay(day, selectedDate);
              const isPast = day < new Date() && !isToday;

              return (
                <button
                  key={idx}
                  onClick={() => !isPast && setSelectedDate(day)}
                  disabled={isPast}
                  className={`p-3 rounded-2xl text-center transition-all ${
                    isSelected
                      ? 'bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] text-white shadow-lg'
                      : isPast
                      ? 'opacity-30 cursor-not-allowed'
                      : 'hover:bg-white/40 bg-white/60'
                  }`}
                >
                  <div className="text-xs text-gray-600 mb-1">
                    {format(day, 'EEE', { locale: vi })}
                  </div>
                  <div className={`text-lg font-semibold ${isSelected ? 'text-white' : 'text-gray-800'}`}>
                    {format(day, 'd')}
                  </div>
                  {isToday && !isSelected && (
                    <div className="w-1 h-1 bg-[#4A9FD8] rounded-full mx-auto mt-1"></div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Time Slots */}
        {selectedDate && (
          <div className="bg-white/40 backdrop-blur-sm rounded-2xl p-4 border border-white/40">
            <h3 className="font-semibold text-gray-800 mb-4">Chọn giờ khám</h3>
            <div className="grid grid-cols-4 gap-2">
              {getAvailableSlots(selectedDate).map(time => (
                <button
                  key={time}
                  onClick={() => setSelectedTime(time)}
                  className={`p-3 rounded-xl text-sm font-medium transition-all ${
                    selectedTime === time
                      ? 'bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] text-white shadow-lg'
                      : 'bg-white/60 hover:bg-white/80 text-gray-700'
                  }`}
                >
                  {time}
                </button>
              ))}
            </div>
            {getAvailableSlots(selectedDate).length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">
                Không có khung giờ trống trong ngày này
              </p>
            )}
          </div>
        )}

        {/* Appointment Type */}
        {selectedDate && selectedTime && (
          <div className="bg-white/40 backdrop-blur-sm rounded-2xl p-4 border border-white/40">
            <h3 className="font-semibold text-gray-800 mb-4">Loại khám</h3>
            <div className="grid grid-cols-2 gap-2">
              {appointmentTypes.map(type => (
                <button
                  key={type.value}
                  onClick={() => setSelectedType(type.value)}
                  className={`p-3 rounded-xl text-sm font-medium transition-all text-left ${
                    selectedType === type.value
                      ? 'bg-gradient-to-br from-[#4A9FD8] to-[#2D88C4] text-white shadow-lg'
                      : 'bg-white/60 hover:bg-white/80 text-gray-700'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {selectedDate && selectedTime && (
          <div className="bg-white/40 backdrop-blur-sm rounded-2xl p-4 border border-white/40">
            <h3 className="font-semibold text-gray-800 mb-4">Ghi chú (tùy chọn)</h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Mô tả triệu chứng hoặc lý do khám..."
              className="w-full px-4 py-3 border border-gray-200/40 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#4A9FD8]/30 bg-white/60 backdrop-blur-sm text-sm resize-none"
              rows={4}
            />
          </div>
        )}
      </div>

      {/* Booking Summary & Submit */}
      {selectedDate && selectedTime && (
        <div className="p-6 border-t border-gray-200/30 bg-white/40 backdrop-blur-sm">
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white/40 mb-4">
            <h4 className="font-semibold text-gray-800 mb-3">Thông tin lịch khám</h4>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Ngày khám:</span>
                <span className="font-medium text-gray-800">
                  {format(selectedDate, 'd MMMM yyyy', { locale: vi })}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Giờ khám:</span>
                <span className="font-medium text-gray-800">{selectedTime}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Loại khám:</span>
                <span className="font-medium text-gray-800">
                  {appointmentTypes.find(t => t.value === selectedType)?.label}
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={handleBooking}
            className="w-full py-3 bg-gradient-to-r from-[#4A9FD8] to-[#2D88C4] text-white rounded-2xl font-semibold hover:shadow-lg transition-all flex items-center justify-center gap-2"
          >
            <CalendarIcon className="w-5 h-5" />
            Xác nhận đặt lịch
          </button>
        </div>
      )}
    </div>
  );
}
