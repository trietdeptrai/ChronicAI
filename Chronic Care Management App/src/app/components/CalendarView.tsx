import { useState } from 'react';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, MapPin, User } from 'lucide-react';
import { Appointment, mockAppointments, appointmentTypes } from '@/data/appointmentData';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isSameDay, addMonths, subMonths, startOfWeek, endOfWeek } from 'date-fns';
import { vi } from 'date-fns/locale';

export function CalendarView() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [appointments] = useState<Appointment[]>(mockAppointments);

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const startDate = startOfWeek(monthStart, { locale: vi });
  const endDate = endOfWeek(monthEnd, { locale: vi });
  const dateRange = eachDayOfInterval({ start: startDate, end: endDate });

  const getAppointmentsForDate = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return appointments.filter(apt => apt.date === dateStr && apt.status === 'scheduled');
  };

  const selectedDateAppointments = getAppointmentsForDate(selectedDate).sort((a, b) => 
    a.time.localeCompare(b.time)
  );

  const getAppointmentTypeColor = (type: Appointment['type']) => {
    return appointmentTypes.find(t => t.value === type)?.color || 'bg-gray-100 text-gray-700';
  };

  const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));

  return (
    <div className="h-full flex gap-6">
      {/* Calendar */}
      <div className="flex-1">
        <div className="bg-[rgba(255,255,255,0.4)] rounded-[24px] p-6 border border-white shadow-[0px_8px_30px_0px_rgba(0,0,0,0.04)] h-full">
          {/* Calendar Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-[#1e2939]">
              {format(currentDate, 'MMMM yyyy', { locale: vi })}
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={prevMonth}
                className="p-2 hover:bg-[rgba(255,255,255,0.6)] rounded-[14px] transition-colors"
              >
                <ChevronLeft className="w-5 h-5 text-[#4a5565]" />
              </button>
              <button
                onClick={() => setCurrentDate(new Date())}
                className="px-4 py-2 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] text-white rounded-[14px] text-sm font-medium shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)] hover:shadow-lg transition-all"
              >
                Hôm nay
              </button>
              <button
                onClick={nextMonth}
                className="p-2 hover:bg-[rgba(255,255,255,0.6)] rounded-[14px] transition-colors"
              >
                <ChevronRight className="w-5 h-5 text-[#4a5565]" />
              </button>
            </div>
          </div>

          {/* Day Headers */}
          <div className="grid grid-cols-7 gap-2 mb-2">
            {['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'].map(day => (
              <div key={day} className="text-center text-sm font-semibold text-[#4a5565] py-2">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-2">
            {dateRange.map((date, idx) => {
              const dayAppointments = getAppointmentsForDate(date);
              const isToday = isSameDay(date, new Date());
              const isSelected = isSameDay(date, selectedDate);
              const isCurrentMonth = isSameMonth(date, currentDate);

              return (
                <button
                  key={idx}
                  onClick={() => setSelectedDate(date)}
                  className={`aspect-square p-2 rounded-[16px] text-sm transition-all relative ${
                    isSelected
                      ? 'bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] text-white shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]'
                      : isToday
                      ? 'bg-[rgba(74,159,216,0.1)] text-[#4a9fd8] font-semibold'
                      : isCurrentMonth
                      ? 'hover:bg-[rgba(255,255,255,0.6)] text-[#364153]'
                      : 'text-[#99a1af]'
                  }`}
                >
                  <div className="font-medium">{format(date, 'd')}</div>
                  {dayAppointments.length > 0 && (
                    <div className={`absolute bottom-1 left-1/2 -translate-x-1/2 flex gap-0.5`}>
                      {dayAppointments.slice(0, 3).map((apt, i) => (
                        <div
                          key={i}
                          className={`w-1 h-1 rounded-full ${
                            isSelected ? 'bg-white' : 'bg-[#4a9fd8]'
                          }`}
                        />
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Legend */}
          <div className="mt-6 pt-6 border-t border-[rgba(229,231,235,0.5)]">
            <h3 className="text-sm font-semibold text-[#364153] mb-3">Loại lịch hẹn</h3>
            <div className="grid grid-cols-2 gap-2">
              {appointmentTypes.map(type => (
                <div key={type.value} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${type.color.split(' ')[0]}`}></div>
                  <span className="text-sm text-[#4a5565]">{type.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Appointments List */}
      <div className="w-96">
        <div className="bg-[rgba(255,255,255,0.4)] rounded-[24px] p-6 border border-white shadow-[0px_8px_30px_0px_rgba(0,0,0,0.04)] h-full flex flex-col">
          <div className="mb-4">
            <h3 className="text-lg font-bold text-[#1e2939] mb-1">
              {format(selectedDate, 'EEEE, d MMMM yyyy', { locale: vi })}
            </h3>
            <p className="text-sm text-[#4a5565]">
              {selectedDateAppointments.length} lịch hẹn
            </p>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3">
            {selectedDateAppointments.length > 0 ? (
              selectedDateAppointments.map(appointment => (
                <div
                  key={appointment.id}
                  className="bg-[rgba(255,255,255,0.6)] rounded-[16px] p-4 border border-[rgba(255,255,255,0.4)] hover:shadow-[0px_4px_12px_0px_rgba(0,0,0,0.06)] transition-all"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-[#4a9fd8]" />
                      <span className="font-semibold text-[#1e2939]">
                        {appointment.time}
                      </span>
                      <span className="text-sm text-[#4a5565]">
                        ({appointment.duration} phút)
                      </span>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${getAppointmentTypeColor(appointment.type)}`}>
                      {appointmentTypes.find(t => t.value === appointment.type)?.label}
                    </span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-[#4a5565]" />
                      <span className="font-medium text-[#1e2939]">{appointment.patientName}</span>
                    </div>

                    {appointment.location && (
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-[#4a5565]" />
                        <span className="text-sm text-[#4a5565]">{appointment.location}</span>
                      </div>
                    )}

                    {appointment.notes && (
                      <p className="text-sm text-[#4a5565] mt-2 pl-6">
                        {appointment.notes}
                      </p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-[#99a1af]">
                <CalendarIcon className="w-12 h-12 mb-3 opacity-20" />
                <p className="text-sm">Không có lịch hẹn</p>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="mt-4 pt-4 border-t border-[rgba(229,231,235,0.5)] grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-[#1e2939]">
                {appointments.filter(a => a.status === 'scheduled').length}
              </div>
              <div className="text-xs text-[#4a5565]">Đã lên lịch</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[#1e2939]">
                {appointments.filter(a => a.status === 'completed').length}
              </div>
              <div className="text-xs text-[#4a5565]">Đã hoàn thành</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}