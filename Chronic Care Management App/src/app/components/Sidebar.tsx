import { LayoutDashboard, Users, Calendar, BarChart3, Settings, MessageSquare } from 'lucide-react';
import { useState } from 'react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'patients', icon: Users, label: 'Patients' },
    { id: 'calendar', icon: Calendar, label: 'Calendar' },
    { id: 'analytics', icon: BarChart3, label: 'Analytics' },
    { id: 'chat', icon: MessageSquare, label: 'AI Chat' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="w-20 bg-[rgba(255,255,255,0.4)] border-r border-[rgba(255,255,255,0.3)] flex flex-col items-center py-6 gap-4">
      {/* Logo */}
      <div className="w-12 h-12 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[16px] flex items-center justify-center mb-4 shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]">
        <LayoutDashboard className="w-6 h-6 text-white" />
      </div>

      {/* Menu Items */}
      <div className="flex flex-col gap-2 w-full px-3">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full h-12 rounded-[14px] flex items-center justify-center transition-all ${
                isActive
                  ? 'bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]'
                  : 'hover:bg-[rgba(255,255,255,0.6)]'
              }`}
              title={item.label}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-[#4a5565]'}`} />
            </button>
          );
        })}
      </div>
    </div>
  );
}