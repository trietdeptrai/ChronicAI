import { useState } from 'react';
import { User, Mail, Phone, Stethoscope, FileText, Save } from 'lucide-react';

export function SettingsPage() {
  const [formData, setFormData] = useState({
    fullName: 'Dr. Ashlynn',
    email: 'dr.ashlynn@medicare.com',
    phone: '+84 123 456 789',
    specialization: 'Internal Medicine',
    licenseNumber: 'MD-12345-VN',
  });

  const [isSaved, setIsSaved] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setIsSaved(false);
  };

  const handleSave = () => {
    // In a real app, this would save to a database
    console.log('Saving settings:', formData);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#1e2939] mb-2">Settings</h1>
        <p className="text-[#4a5565]">Manage your account information and preferences</p>
      </div>

      {/* Profile Section */}
      <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-8 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
        <div className="flex items-center gap-6 mb-8">
          <div className="w-24 h-24 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] rounded-[24px] flex items-center justify-center">
            <span className="text-white text-3xl font-semibold">DA</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-[#1e2939] mb-1">Profile Picture</h2>
            <p className="text-sm text-[#4a5565] mb-3">Update your profile photo</p>
            <button className="px-4 py-2 bg-[rgba(74,159,216,0.15)] text-[#4A9FD8] rounded-[14px] text-sm font-medium hover:bg-[rgba(74,159,216,0.25)] transition-colors">
              Change Photo
            </button>
          </div>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent mb-8"></div>

        {/* Form Fields */}
        <div className="space-y-6">
          {/* Full Name */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#1e2939] mb-3">
              <User className="w-4 h-4 text-[#4A9FD8]" />
              Full Name
            </label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-[#1e2939]"
              placeholder="Enter your full name"
            />
          </div>

          {/* Email */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#1e2939] mb-3">
              <Mail className="w-4 h-4 text-[#4A9FD8]" />
              Email Address
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-[#1e2939]"
              placeholder="Enter your email"
            />
          </div>

          {/* Phone */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#1e2939] mb-3">
              <Phone className="w-4 h-4 text-[#4A9FD8]" />
              Phone Number
            </label>
            <input
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-[#1e2939]"
              placeholder="Enter your phone number"
            />
          </div>

          {/* Specialization */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#1e2939] mb-3">
              <Stethoscope className="w-4 h-4 text-[#4A9FD8]" />
              Specialization
            </label>
            <input
              type="text"
              name="specialization"
              value={formData.specialization}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-[#1e2939]"
              placeholder="Enter your specialization"
            />
          </div>

          {/* License Number */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#1e2939] mb-3">
              <FileText className="w-4 h-4 text-[#4A9FD8]" />
              Medical License Number
            </label>
            <input
              type="text"
              name="licenseNumber"
              value={formData.licenseNumber}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-[rgba(255,255,255,0.8)] border border-[rgba(255,255,255,0.4)] rounded-[16px] focus:outline-none focus:ring-2 focus:ring-[#4a9fd8]/30 text-[#1e2939]"
              placeholder="Enter your license number"
            />
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center gap-4 mt-8">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-b from-[#4a9fd8] to-[#2d88c4] text-white rounded-[16px] font-semibold hover:shadow-lg transition-all"
          >
            <Save className="w-5 h-5" />
            Save Changes
          </button>
          {isSaved && (
            <span className="text-green-600 font-medium animate-fade-in">
              ✓ Changes saved successfully!
            </span>
          )}
        </div>
      </div>

      {/* Preferences Section */}
      <div className="bg-[rgba(255,255,255,0.6)] backdrop-blur-md rounded-3xl p-8 border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
        <h2 className="text-xl font-bold text-[#1e2939] mb-6">Preferences</h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-[rgba(255,255,255,0.5)] rounded-[16px]">
            <div>
              <div className="font-semibold text-[#1e2939] mb-1">Email Notifications</div>
              <div className="text-sm text-[#4a5565]">Receive email alerts for critical events</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[#4a9fd8]/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#4A9FD8]"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-[rgba(255,255,255,0.5)] rounded-[16px]">
            <div>
              <div className="font-semibold text-[#1e2939] mb-1">SMS Alerts</div>
              <div className="text-sm text-[#4a5565]">Get text messages for urgent patient updates</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[#4a9fd8]/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#4A9FD8]"></div>
            </label>
          </div>

          <div className="flex items-center justify-between p-4 bg-[rgba(255,255,255,0.5)] rounded-[16px]">
            <div>
              <div className="font-semibold text-[#1e2939] mb-1">Calendar Reminders</div>
              <div className="text-sm text-[#4a5565]">Reminders for upcoming appointments</div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[#4a9fd8]/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#4A9FD8]"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}