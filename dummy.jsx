import React, { useState, useEffect, useRef } from 'react';
import { 
  Menu, X, Send, Search, MapPin, BookOpen, User, 
  MessageSquare, AlertCircle, ChevronRight, LogOut, Info, 
  Eye, Phone, FileText, Calendar, Clock, Activity, ShieldCheck,
  Settings, Bell, Trash2, Map, List, Filter, Plus
} from 'lucide-react';

// --- API CONFIGURATION ---
const apiKey = ""; // API key is provided by the execution environment

// --- MOCK DATA ---
const mockFacilities = [
  { id: 1, name: "Korle Bu Teaching Hospital", type: "Hospital", region: "Greater Accra", status: "Accredited", lat: 5.5385, lng: -0.2246 },
  { id: 2, name: "Ridge Hospital", type: "Hospital", region: "Greater Accra", status: "Accredited", lat: 5.5600, lng: -0.1989 },
  { id: 3, name: "Komfo Anokye Teaching Hospital", type: "Hospital", region: "Ashanti", status: "Accredited", lat: 6.6980, lng: -1.6288 },
  { id: 4, name: "Tafo Government Hospital", type: "Hospital", region: "Ashanti", status: "Accredited", lat: 6.7261, lng: -1.6111 },
  { id: 5, name: "Cape Coast Teaching Hospital", type: "Hospital", region: "Central", status: "Accredited", lat: 5.1430, lng: -1.2780 },
  { id: 6, name: "Ernest Chemist Pharmacy", type: "Pharmacy", region: "Greater Accra", status: "Accredited", lat: 5.5557, lng: -0.1963 },
  { id: 7, name: "Medlab Diagnostics", type: "Diagnostic", region: "Greater Accra", status: "Accredited", lat: 5.5700, lng: -0.1800 },
];

const mockUpdates = [
  { id: 1, title: "New Antimalarial Drugs Added to NHIS Formulary", date: "24 May, 2025", source: "NHIS Official", category: "Drug Formulary" },
  { id: 2, title: "Nationwide Polio Vaccination Campaign", date: "12 March, 2025", source: "Ghana Health Service", category: "Disease Alerts" },
  { id: 3, title: "Digital Renewal System Maintenance", date: "05 March, 2025", source: "NHIS IT Dept", category: "Policy Updates" },
  { id: 4, title: "Maternal Care Package Expanded", date: "18 Feb, 2025", source: "NHIS Official", category: "Policy Updates" },
  { id: 5, title: "Cholera Outbreak Precautionary Measures", date: "10 Feb, 2025", source: "Ghana Health Service", category: "Disease Alerts" },
];

const mockResources = [
  { id: 1, title: "Understanding Your NHIS Card", category: "Membership", readTime: "3 min" },
  { id: 2, title: "What Services Are Excluded?", category: "Covered Services", readTime: "5 min" },
  { id: 3, title: "How to Dispute an Unfair Charge", category: "Your Rights", readTime: "4 min" },
  { id: 4, title: "Checking if Your Medication is Covered", category: "Medicines Guide", readTime: "2 min" },
  { id: 5, title: "Enrollment & Renewal Steps", category: "Enrollment", readTime: "4 min" },
  { id: 6, title: "Frequently Asked Questions", category: "FAQs", readTime: "6 min" },
];

const regions = ["All Regions", "Greater Accra", "Ashanti", "Central", "Western", "Eastern", "Northern", "Volta"];
const facilityTypes = ["All Types", "Hospital", "Clinic", "Pharmacy", "Diagnostic"];

// --- MAIN APPLICATION COMPONENT ---
export default function App() {
  const [user, setUser] = useState(null);
  const [currentPage, setCurrentPage] = useState('landing');

  // Authentication Handlers
  const handleLogin = (e) => {
    e.preventDefault();
    setUser({ 
      name: "Kwame Mensah", 
      email: "subscriber@example.com",
      phone: "054 123 4567",
      region: "Greater Accra",
      nhisNumber: "21789057", 
      type: "Standard", 
      expiry: "24 May, 2026",
      age: "32 years old",
      gender: "Male",
      occupation: "Teacher"
    });
    setCurrentPage('dashboard');
  };

  const handleSignUp = (e) => {
    e.preventDefault();
    setUser({ 
      name: e.target.fullName.value, 
      email: e.target.email.value,
      phone: e.target.phone.value,
      region: e.target.region.value,
      nhisNumber: e.target.nhisNumber.value, 
      type: e.target.membershipType.value, 
      expiry: "Pending Activation",
      age: "Not specified",
      gender: "Not specified",
      occupation: "Not specified"
    });
    setCurrentPage('dashboard');
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentPage('landing');
  };

  const navigateTo = (page) => {
    setCurrentPage(page);
  };

  // Render appropriate layout based on state
  if (currentPage === 'landing' || currentPage === 'login' || currentPage === 'signup') {
    return <AuthLayout currentPage={currentPage} handleLogin={handleLogin} handleSignUp={handleSignUp} navigateTo={navigateTo} />;
  }

  return (
    <DashboardLayout 
      user={user} 
      currentPage={currentPage} 
      navigateTo={navigateTo} 
      handleLogout={handleLogout} 
    />
  );
}

// --- LAYOUTS ---

function AuthLayout({ currentPage, handleLogin, handleSignUp, navigateTo }) {
  return (
    <div className="min-h-screen md:h-screen w-full bg-white font-sans flex">
      <div className="w-full h-full flex flex-col md:flex-row">
        
        {/* Left Side - Image & Info Panel */}
        <div className="w-full md:w-1/2 flex flex-col min-h-[100vh] md:min-h-0 md:h-full border-r border-slate-100 shrink-0">
          
          {/* Top Image Section */}
          <div 
            className="h-[40vh] md:h-[55%] w-full bg-cover bg-center bg-no-repeat shrink-0"
            style={{ backgroundImage: "url('https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?q=80&w=1000&auto=format&fit=crop')" }}
          ></div>
          
          {/* Bottom Blue Content Section */}
          <div className="flex-1 bg-[#3454D1] text-white p-8 md:p-12 lg:p-16 flex flex-col justify-center shrink-0">
            <div className="flex items-center gap-3 mb-8">
              <ShieldCheck size={28} className="text-white" strokeWidth={2.5} />
              <span className="font-bold text-2xl tracking-wide">NHIS Agent</span>
            </div>

            <div className="flex">
              <div className="w-1 bg-white mr-5 mt-1 rounded-full shrink-0"></div>
              <div>
                <h1 className="text-[22px] md:text-2xl font-normal leading-snug mb-3">
                  Welcome to <span className="font-bold">NHIS Agent</span><br/>
                  <span className="font-bold">Patient Rights & Entitlement</span>
                </h1>
                <p className="text-blue-100/90 text-[13px] leading-relaxed max-w-sm">
                  Cloud Based Streamline Healthcare Management system with centralized user friendly platform to understand coverage and navigate care.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Action Panel */}
        <div className="w-full md:w-1/2 p-8 md:p-12 lg:p-16 flex items-center justify-center bg-white h-full overflow-y-auto">
          <div className="w-full max-w-[400px] mx-auto py-8">
            
            <div className="flex items-center gap-3 mb-10 text-[#3454D1]">
              <ShieldCheck size={32} strokeWidth={2.5} />
              <span className="font-bold text-2xl tracking-wide text-[#3454D1]">NHIS Agent</span>
            </div>

            {currentPage === 'landing' && (
              <div className="flex flex-col gap-6 animate-in fade-in duration-500">
                <h2 className="text-[32px] font-bold text-slate-800 mb-1">Welcome</h2>
                <p className="text-[15px] font-medium text-slate-600 mb-6">
                  Access the platform to check your coverage entitlements and find accredited facilities.
                </p>
                
                <button 
                  onClick={() => navigateTo('login')}
                  className="w-full bg-[#3454D1] text-white rounded-lg py-3.5 font-semibold hover:bg-blue-700 transition-colors"
                >
                  Sign In
                </button>
                <button 
                  onClick={() => navigateTo('signup')}
                  className="w-full bg-slate-50 text-[#3454D1] rounded-lg py-3.5 font-semibold hover:bg-slate-100 transition-colors border border-slate-200"
                >
                  Create an Account
                </button>
              </div>
            )}

            {currentPage === 'login' && (
              <div className="flex flex-col animate-in fade-in duration-500">
                <h2 className="text-[32px] font-bold text-slate-800 mb-1">Login</h2>
                <p className="text-[15px] font-medium text-slate-600 mb-8">Enter your credentials to login to your account</p>
                
                <form onSubmit={handleLogin} className="flex flex-col gap-5">
                  <div className="flex flex-col gap-2">
                    <label className="text-[13px] font-bold text-slate-800">Email</label>
                    <input 
                      type="email" 
                      required
                      defaultValue="subscriber@example.com"
                      className="border border-slate-200 rounded-lg p-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] focus:border-[#3454D1] text-slate-800"
                    />
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    <label className="text-[13px] font-bold text-slate-800">Password</label>
                    <div className="relative">
                      <input 
                        type="password" 
                        required
                        defaultValue="****************"
                        className="w-full border border-slate-200 rounded-lg p-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] focus:border-[#3454D1] text-slate-500 tracking-widest"
                      />
                      <Eye className="absolute right-4 top-4 text-slate-300 cursor-pointer hover:text-slate-500" size={20} />
                    </div>
                  </div>
                  
                  <div className="flex justify-end mb-1 mt-1">
                    <span className="text-[13px] text-[#3454D1] font-semibold cursor-pointer hover:underline">Forgot Password?</span>
                  </div>

                  <button type="submit" className="w-full bg-[#3454D1] text-white rounded-lg py-3.5 font-semibold hover:bg-blue-700 transition-colors mt-2">
                    Sign In
                  </button>
                </form>
                
                <p className="mt-8 text-[14px] text-slate-800 font-medium text-center">
                  Don't have an account? <span onClick={() => navigateTo('signup')} className="font-semibold text-[#3454D1] cursor-pointer hover:underline">Sign Up</span>
                </p>
              </div>
            )}

            {currentPage === 'signup' && (
              <div className="flex flex-col animate-in fade-in duration-500">
                <h2 className="text-[32px] font-bold text-slate-800 mb-1">Sign Up</h2>
                <p className="text-[15px] font-medium text-slate-600 mb-6">Create an account to track your NHIS benefits</p>
                
                <form onSubmit={handleSignUp} className="flex flex-col gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[13px] font-bold text-slate-800">Full Name</label>
                    <input name="fullName" type="text" required placeholder="e.g. Kwame Mensah" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
                  </div>
                  
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[13px] font-bold text-slate-800">Email Address</label>
                    <input name="email" type="email" required placeholder="kwame@example.com" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[13px] font-bold text-slate-800">Phone (Optional)</label>
                      <input name="phone" type="tel" placeholder="054 123 4567" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[13px] font-bold text-slate-800">Region</label>
                      <select name="region" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] bg-white">
                        {regions.filter(r => r !== "All Regions").map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[13px] font-bold text-slate-800">NHIS Number</label>
                      <input name="nhisNumber" type="text" required placeholder="8 digit number" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[13px] font-bold text-slate-800">Membership</label>
                      <select name="membershipType" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] bg-white">
                        <option value="Standard">Standard</option>
                        <option value="Informal">Informal</option>
                        <option value="SSNIT">SSNIT</option>
                        <option value="Indigent">Indigent</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-[13px] font-bold text-slate-800">Password</label>
                    <input type="password" required placeholder="Create a strong password" className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
                  </div>

                  <button type="submit" className="w-full bg-[#3454D1] text-white rounded-lg py-3.5 font-semibold hover:bg-blue-700 transition-colors mt-4">
                    Create Account
                  </button>
                </form>
                
                <p className="mt-6 text-[14px] text-slate-800 font-medium text-center">
                  Already have an account? <span onClick={() => navigateTo('login')} className="font-semibold text-[#3454D1] cursor-pointer hover:underline">Log In</span>
                </p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

function DashboardLayout({ user, currentPage, navigateTo, handleLogout }) {
  const tabs = [
    { id: 'dashboard', label: 'Overview' },
    { id: 'chat', label: 'Agent Chat' },
    { id: 'facilities', label: 'Facilities' },
    { id: 'updates', label: 'Health Updates' },
    { id: 'resources', label: 'Resources' },
  ];

  return (
    <div className="min-h-screen bg-[#DDE5ED] text-slate-800 font-sans pb-10 flex flex-col">
      {/* Top Header */}
      <div className="bg-white px-6 md:px-12 pt-6 pb-0 rounded-b-3xl border-b border-slate-200 mb-6 shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto">
          {/* Breadcrumb / Title area */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2 text-slate-500 font-medium">
              <span className="cursor-pointer hover:text-slate-800" onClick={() => navigateTo('dashboard')}>NHIS Portal</span>
              <ChevronRight size={16} />
              <span className="text-slate-900 font-semibold">{user ? user.name : 'Guest'}</span>
            </div>
            
            <div className="flex items-center gap-6">
              <button onClick={() => navigateTo('profile')} className="text-slate-500 hover:text-[#3454D1] transition-colors flex items-center gap-2 text-sm font-medium">
                <Settings size={18} />
                <span className="hidden sm:inline">Settings</span>
              </button>
              <button onClick={handleLogout} className="text-slate-500 hover:text-red-500 transition-colors flex items-center gap-2 text-sm font-medium">
                <LogOut size={18} />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex overflow-x-auto hide-scrollbar gap-8">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => navigateTo(tab.id)}
                className={`pb-4 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${
                  currentPage === tab.id 
                    ? 'border-[#3454D1] text-[#3454D1]' 
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="max-w-6xl mx-auto px-4 md:px-6 w-full flex-grow flex flex-col">
        {currentPage === 'dashboard' && <Dashboard user={user} navigateTo={navigateTo} />}
        {currentPage === 'chat' && <ChatPage />}
        {currentPage === 'facilities' && <FacilitiesPage />}
        {currentPage === 'updates' && <UpdatesPage />}
        {currentPage === 'resources' && <ResourcesPage />}
        {currentPage === 'profile' && <ProfileSettingsPage user={user} />}
      </main>
    </div>
  );
}

// --- PAGE COMPONENTS ---

function Dashboard({ user, navigateTo }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in duration-300">
      
      {/* Left Column (Main Data) */}
      <div className="lg:col-span-2 flex flex-col gap-6">
        
        {/* Profile Card */}
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 border-b border-slate-100 pb-6 gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-blue-50 text-[#3454D1] rounded-2xl flex items-center justify-center shrink-0">
                <User size={28} strokeWidth={2.5} />
              </div>
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-xl font-bold text-slate-900">{user.name}</h2>
                  <span className="text-sm font-medium text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md">ID: {user.nhisNumber}</span>
                </div>
                <p className="text-slate-500 text-sm mt-1">
                  {user.age} • {user.gender} • {user.occupation}
                </p>
              </div>
            </div>
            
            <button className="w-full sm:w-auto bg-[#3454D1] text-white px-6 py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-700 transition-colors shadow-sm">
              Renew Membership
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div>
              <p className="text-xs text-slate-400 mb-1">Status</p>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <p className="font-semibold text-slate-800">Active</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Membership</p>
              <p className="font-semibold text-slate-800">{user.type}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Est. Expiry</p>
              <p className="font-semibold text-slate-800">{user.expiry}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Region</p>
              <p className="font-semibold text-slate-800">{user.region}</p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-lg text-slate-800">Quick Actions</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button onClick={() => navigateTo('chat')} className="flex flex-col items-center justify-center p-6 border border-slate-100 rounded-2xl hover:border-[#3454D1] hover:bg-blue-50/50 transition-all group shadow-sm">
              <div className="w-12 h-12 rounded-full bg-blue-50 text-[#3454D1] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <MessageSquare size={20} />
              </div>
              <span className="font-bold text-slate-800 text-sm">Ask the Agent</span>
              <span className="text-xs text-slate-500 mt-1 text-center">Check drug coverage</span>
            </button>
            
            <button onClick={() => navigateTo('facilities')} className="flex flex-col items-center justify-center p-6 border border-slate-100 rounded-2xl hover:border-indigo-400 hover:bg-indigo-50/50 transition-all group shadow-sm">
              <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <MapPin size={20} />
              </div>
              <span className="font-bold text-slate-800 text-sm">Find Facility</span>
              <span className="text-xs text-slate-500 mt-1 text-center">Locate hospitals</span>
            </button>
            
            <button onClick={() => navigateTo('resources')} className="flex flex-col items-center justify-center p-6 border border-slate-100 rounded-2xl hover:border-emerald-400 hover:bg-emerald-50/50 transition-all group shadow-sm">
              <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <AlertCircle size={20} />
              </div>
              <span className="font-bold text-slate-800 text-sm">Review Rights</span>
              <span className="text-xs text-slate-500 mt-1 text-center">Resolve disputes</span>
            </button>
          </div>
        </div>

        {/* Recent Queries */}
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-lg text-slate-800">Recent Conversations</h3>
            <span onClick={() => navigateTo('chat')} className="text-[#3454D1] text-sm font-semibold cursor-pointer flex items-center gap-1 hover:underline">
              View all <ChevronRight size={14} />
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-slate-400 text-xs border-b border-slate-100">
                  <th className="pb-3 font-medium w-1/2">Query Topic</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-50 group hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => navigateTo('chat')}>
                  <td className="py-4 px-2 rounded-l-lg">
                    <p className="font-semibold text-slate-800 mb-1">Is dialysis covered?</p>
                    <p className="text-xs text-slate-500 truncate max-w-[200px]">Checking chronic treatments policy</p>
                  </td>
                  <td className="py-4">
                    <span className="bg-emerald-50 text-emerald-600 text-[11px] font-semibold px-2.5 py-1 rounded-md">Coverage</span>
                  </td>
                  <td className="py-4 text-sm text-slate-600">Yesterday</td>
                  <td className="py-4 text-sm text-slate-600 rounded-r-lg">Resolved</td>
                </tr>
                <tr className="group hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => navigateTo('chat')}>
                  <td className="py-4 px-2 rounded-l-lg">
                    <p className="font-semibold text-slate-800 mb-1">Accredited pharmacies</p>
                    <p className="text-xs text-slate-500 truncate max-w-[200px]">Looking for facilities in Osu area</p>
                  </td>
                  <td className="py-4">
                    <span className="bg-blue-50 text-[#3454D1] text-[11px] font-semibold px-2.5 py-1 rounded-md">Facility</span>
                  </td>
                  <td className="py-4 text-sm text-slate-600">18 May, 2025</td>
                  <td className="py-4 text-sm text-slate-600 rounded-r-lg">Resolved</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Right Column (Timeline / Updates) */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm h-full flex flex-col">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-bold text-lg text-slate-800">Latest Updates</h3>
            <span onClick={() => navigateTo('updates')} className="text-[#3454D1] text-sm font-semibold cursor-pointer flex items-center gap-1 hover:underline">
              See all <ChevronRight size={14} />
            </span>
          </div>

          <div className="flex flex-col gap-8 flex-grow">
            {/* Upcoming Section */}
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Upcoming Events</p>
              
              <div className="relative pl-6 border-l-2 border-[#3454D1]">
                <div className="absolute w-3 h-3 bg-white border-2 border-[#3454D1] rounded-full -left-[7.5px] top-1"></div>
                
                <h4 className="font-bold text-slate-800 text-md">Drug Formulary Update</h4>
                <p className="text-sm text-slate-500 mt-1 mb-4">24 May, 2025</p>
                
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <p className="text-sm text-slate-600 mb-3 leading-relaxed">
                    New antimalarial drugs are scheduled to be added to the NHIS formulary.
                  </p>
                  <div className="flex items-center gap-4 text-xs font-medium border-t border-slate-200 pt-3">
                    <div>
                      <p className="text-slate-400 mb-0.5">Source</p>
                      <p className="text-slate-800">NHIS Official</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Past Section */}
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Recent Announcements</p>
              
              <div className="flex flex-col gap-6">
                <div className="relative pl-6 border-l-2 border-slate-200">
                  <div className="absolute w-3 h-3 bg-slate-200 rounded-full -left-[7px] top-1"></div>
                  <h4 className="font-semibold text-slate-700">Polio Vaccination Campaign</h4>
                  <p className="text-sm text-slate-400 mt-1">12 March, 2025</p>
                </div>
                
                <div className="relative pl-6 border-l-2 border-slate-200">
                  <div className="absolute w-3 h-3 bg-slate-200 rounded-full -left-[7px] top-1"></div>
                  <h4 className="font-semibold text-slate-700">Digital System Maintenance</h4>
                  <p className="text-sm text-slate-400 mt-1">05 March, 2025</p>
                </div>
              </div>
            </div>

          </div>
          
          <button onClick={() => navigateTo('updates')} className="w-full mt-6 py-3 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold rounded-xl transition-colors border border-slate-200 text-sm">
            Go to Health Updates
          </button>
        </div>
      </div>

    </div>
  );
}

function FacilitiesPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("All Regions");
  const [selectedType, setSelectedType] = useState("All Types");
  const [viewMode, setViewMode] = useState("list"); // 'list' or 'map'
  
  const filtered = mockFacilities.filter(f => {
    const matchesSearch = f.name.toLowerCase().includes(searchTerm.toLowerCase()) || f.region.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRegion = selectedRegion === "All Regions" || f.region === selectedRegion;
    const matchesType = selectedType === "All Types" || f.type === selectedType;
    return matchesSearch && matchesRegion && matchesType;
  });

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm flex flex-col animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Accredited Facilities</h1>
          <p className="text-slate-500 mt-1 text-sm">Find hospitals, clinics, and pharmacies that accept NHIS.</p>
        </div>
        
        {/* Toggle View */}
        <div className="flex bg-slate-100 p-1 rounded-lg self-start md:self-end">
          <button 
            onClick={() => setViewMode('list')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${viewMode === 'list' ? 'bg-white text-[#3454D1] shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <List size={16} /> List
          </button>
          <button 
            onClick={() => setViewMode('map')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${viewMode === 'map' ? 'bg-white text-[#3454D1] shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
          >
            <Map size={16} /> Map
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col lg:flex-row gap-4 mb-8 bg-slate-50 p-4 rounded-xl border border-slate-100">
        <div className="flex-grow flex items-center border border-slate-200 rounded-lg px-3 py-2.5 bg-white focus-within:ring-2 focus-within:ring-[#3454D1] transition-all">
          <Search size={18} className="text-slate-400 mr-2 shrink-0" />
          <input 
            type="text" 
            placeholder="Search by name or town..." 
            className="w-full focus:outline-none bg-transparent text-slate-800 text-sm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2.5 bg-white shrink-0">
            <Filter size={18} className="text-slate-400 mr-2" />
            <select 
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="bg-transparent text-slate-800 text-sm focus:outline-none cursor-pointer"
            >
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2.5 bg-white shrink-0">
            <Activity size={18} className="text-slate-400 mr-2" />
            <select 
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-transparent text-slate-800 text-sm focus:outline-none cursor-pointer"
            >
              {facilityTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
      </div>

      {viewMode === 'list' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-grow">
          {filtered.map((facility) => (
            <div key={facility.id} className="border border-slate-100 rounded-xl p-5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)] transition-all bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4 group">
              <div className="flex items-start gap-4">
                <div className="mt-1 w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 flex-shrink-0 group-hover:bg-[#3454D1] group-hover:text-white transition-colors">
                  <MapPin size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">{facility.name}</h3>
                  <p className="text-sm text-slate-500 mt-0.5">{facility.type} • {facility.region}</p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2 self-start sm:self-center">
                <div className="px-3 py-1 bg-emerald-50 text-emerald-600 text-xs font-semibold rounded-md">
                  {facility.status}
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full py-16 text-center text-slate-400 flex flex-col items-center">
              <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                <MapPin size={32} className="text-slate-300" />
              </div>
              <p className="font-medium text-slate-600">No facilities found matching your criteria.</p>
              <button 
                onClick={() => { setSearchTerm(''); setSelectedRegion('All Regions'); setSelectedType('All Types'); }}
                className="mt-4 text-[#3454D1] text-sm font-semibold hover:underline"
              >
                Clear all filters
              </button>
            </div>
          )}
        </div>
      ) : (
        /* Styled Map Placeholder */
        <div className="flex-grow rounded-xl bg-[#E8F0F8] border border-slate-200 relative overflow-hidden min-h-[400px] flex items-center justify-center bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCI+CjxyZWN0IHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZDBlNmYxIiBzdHJva2Utd2lkdGg9IjEiLz4KPC9zdmc+')]">
          
          <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-md border border-slate-100 max-w-xs">
            <h4 className="font-bold text-sm text-slate-800 mb-1">Map View Active</h4>
            <p className="text-xs text-slate-500">Showing {filtered.length} accredited facilities in selected areas.</p>
          </div>

          {filtered.map((facility, idx) => {
            // Distribute dummy pins visually
            const topPos = `${20 + (idx * 15) % 60}%`;
            const leftPos = `${20 + (idx * 25) % 60}%`;
            return (
              <div key={facility.id} className="absolute flex flex-col items-center group cursor-pointer" style={{ top: topPos, left: leftPos }}>
                <div className="bg-white text-slate-800 text-xs font-bold px-2 py-1 rounded shadow-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap mb-1 absolute bottom-full">
                  {facility.name}
                </div>
                <MapPin size={28} className="text-[#3454D1] drop-shadow-md transform group-hover:scale-110 transition-transform -mt-7" fill="white" />
              </div>
            );
          })}
          
          {filtered.length === 0 && (
             <div className="bg-white/90 backdrop-blur-sm px-6 py-4 rounded-xl shadow-sm text-center">
               <p className="font-medium text-slate-600">No facilities to display on map.</p>
             </div>
          )}
        </div>
      )}
    </div>
  );
}

function UpdatesPage() {
  const [activeCategory, setActiveCategory] = useState('All');
  const categories = ['All', 'Policy Updates', 'Drug Formulary', 'Disease Alerts', 'General Health'];

  const filteredUpdates = activeCategory === 'All' 
    ? mockUpdates 
    : mockUpdates.filter(u => u.category === activeCategory);

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm flex flex-col animate-in fade-in duration-300">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Health Updates</h1>
        <p className="text-slate-500 mt-1 text-sm">Curated news, policy changes, and alerts relevant to NHIS subscribers.</p>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2 mb-8">
        {categories.map(cat => (
          <button 
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors border ${
              activeCategory === cat 
                ? 'bg-[#3454D1] text-white border-[#3454D1]' 
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Updates Feed */}
      <div className="flex flex-col gap-4">
        {filteredUpdates.map(update => (
          <div key={update.id} className="border border-slate-100 rounded-xl p-6 hover:shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition-all bg-white flex flex-col sm:flex-row gap-6 group">
            <div className="flex-grow">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#3454D1] bg-blue-50 px-2.5 py-1 rounded-md">
                  {update.category}
                </span>
                <span className="text-sm text-slate-400 font-medium">{update.date}</span>
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2 group-hover:text-[#3454D1] transition-colors">{update.title}</h3>
              <p className="text-sm text-slate-500 line-clamp-2 mb-4">
                Official communication regarding {update.title.toLowerCase()}. Please review this update to understand how it impacts your healthcare coverage and access to facilities.
              </p>
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                <ShieldCheck size={14} className="text-emerald-500" />
                Source: {update.source}
              </div>
            </div>
            <div className="sm:w-32 flex shrink-0 items-center justify-start sm:justify-end">
              <button className="text-[#3454D1] text-sm font-semibold hover:underline flex items-center gap-1">
                Read More <ChevronRight size={16} />
              </button>
            </div>
          </div>
        ))}
        {filteredUpdates.length === 0 && (
          <div className="py-12 text-center text-slate-400">
            <p className="font-medium">No updates found in this category.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ResourcesPage() {
  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm animate-in fade-in duration-300">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Resource Centre</h1>
        <p className="text-slate-500 mt-1 text-sm">Official guidelines, policies, and educational material grounded in NHIS documentation.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {mockResources.map(resource => (
          <div key={resource.id} className="border border-slate-100 rounded-xl p-6 flex flex-col justify-between hover:border-slate-200 hover:shadow-[0_4px_20px_rgba(0,0,0,0.03)] transition-all cursor-pointer group bg-slate-50/50">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-semibold text-[#3454D1] bg-blue-50 px-2.5 py-1 rounded-md">
                  {resource.category}
                </span>
                <BookOpen size={16} className="text-slate-300" />
              </div>
              <h3 className="font-bold text-lg text-slate-800 mb-2 group-hover:text-[#3454D1] transition-colors leading-snug">
                {resource.title}
              </h3>
            </div>
            <div className="flex justify-between items-center mt-8 pt-4 border-t border-slate-100">
              <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                <Clock size={14} />
                {resource.readTime} read
              </span>
              <ChevronRight size={18} className="text-slate-300 group-hover:text-[#3454D1] transition-colors" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProfileSettingsPage({ user }) {
  const [notifications, setNotifications] = useState(true);

  if (!user) return null;

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm animate-in fade-in duration-300 max-w-4xl mx-auto w-full">
      <div className="mb-8 border-b border-slate-100 pb-6 flex items-center gap-4">
        <div className="w-16 h-16 bg-blue-50 text-[#3454D1] rounded-2xl flex items-center justify-center shrink-0">
          <Settings size={32} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Profile & Settings</h1>
          <p className="text-slate-500 mt-1 text-sm">Manage your personal details and app preferences.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        
        {/* Personal Details Form */}
        <div className="flex flex-col gap-6">
          <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2">Personal Information</h3>
          
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">Full Name</label>
              <input type="text" defaultValue={user.name} className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">Email</label>
              <input type="email" defaultValue={user.email} className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">Phone</label>
              <input type="tel" defaultValue={user.phone} className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">Region</label>
              <select defaultValue={user.region} className="border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] bg-white">
                 {regions.filter(r => r !== "All Regions").map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <button className="bg-slate-100 text-slate-700 font-semibold py-3 rounded-lg hover:bg-slate-200 transition-colors mt-2 text-sm">
              Save Changes
            </button>
          </div>
        </div>

        {/* NHIS Details & Preferences */}
        <div className="flex flex-col gap-10">
          
          <div className="flex flex-col gap-6">
            <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2">NHIS Membership</h3>
            
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-slate-500">NHIS Number</span>
                <span className="font-semibold text-slate-800">{user.nhisNumber}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-slate-500">Membership Type</span>
                <span className="font-semibold text-slate-800">{user.type}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-slate-500">Est. Expiry</span>
                <span className="font-semibold text-[#10B981]">{user.expiry}</span>
              </div>
              <button className="w-full bg-white border border-slate-200 text-[#3454D1] font-semibold py-2 rounded-lg hover:bg-slate-50 transition-colors mt-3 text-sm">
                Update NHIS Info
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-6">
            <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2">Preferences & Data</h3>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-50 text-[#3454D1] flex items-center justify-center">
                  <Bell size={18} />
                </div>
                <div>
                  <p className="font-semibold text-slate-800 text-sm">Renewal Reminders</p>
                  <p className="text-xs text-slate-500">Get SMS 30 days before expiry</p>
                </div>
              </div>
              <button 
                onClick={() => setNotifications(!notifications)}
                className={`w-12 h-6 rounded-full transition-colors relative ${notifications ? 'bg-[#3454D1]' : 'bg-slate-300'}`}
              >
                <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${notifications ? 'translate-x-7' : 'translate-x-1'}`}></div>
              </button>
            </div>

            <div className="flex items-center justify-between border-t border-slate-100 pt-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-red-50 text-red-500 flex items-center justify-center">
                  <Trash2 size={18} />
                </div>
                <div>
                  <p className="font-semibold text-slate-800 text-sm">Clear Conversation History</p>
                  <p className="text-xs text-slate-500">Delete all past chats with Agent</p>
                </div>
              </div>
              <button className="text-red-500 text-sm font-semibold hover:underline">
                Clear
              </button>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      text: 'Hello. I am the NHIS Rights & Entitlement Agent. I can help you check drug coverage, find facilities, or understand your rights as a patient. What do you need help with?',
      source: null,
      suggestions: ['Is dialysis covered under NHIS?', 'Find an accredited hospital near me', 'They charged me for Paracetamol. Is that right?']
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef(null);

  const mockHistory = [
    { id: 1, title: 'Dialysis coverage rules', date: 'Yesterday' },
    { id: 2, title: 'Pharmacies in Osu', date: '3 days ago' },
    { id: 3, title: 'Maternity entitlements', date: '1 week ago' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e, forcedInput = null) => {
    e?.preventDefault();
    const userText = forcedInput || input;
    if (!userText.trim()) return;

    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setInput('');
    setIsLoading(true);

    try {
      const systemInstruction = `
        You are the NHIS Patient Rights & Entitlement Agent for Ghana.
        Your goal is to help Ghanaian subscribers understand their National Health Insurance Scheme coverage.
        RULES:
        1. Keep responses clear, concise, and professional. 
        2. Do not use emojis. Do not use em dashes (use single hyphens instead).
        3. YOU MUST ALWAYS append a source attribution at the very end of your response on a new line starting exactly with "SOURCE: ". 
        Example: "SOURCE: NHIS Benefit Package Document, Section 4".
        4. If the user asks something outside NHIS scope or you do not know, say exactly: "I could not find this in the NHIS guidelines. Please contact NHIS directly on 0800-900-9900."
      `;

      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: systemInstruction }] },
          contents: [{ parts: [{ text: userText }] }],
        })
      });

      if (!response.ok) throw new Error('API Error');

      const data = await response.json();
      let agentText = data.candidates?.[0]?.content?.parts?.[0]?.text || "System Error: Could not retrieve response.";
      
      let sourceTag = null;
      const lines = agentText.split('\n');
      const sourceLineIndex = lines.findIndex(line => line.trim().startsWith('SOURCE:'));
      
      if (sourceLineIndex !== -1) {
        sourceTag = lines[sourceLineIndex].replace('SOURCE:', '').trim();
        agentText = lines.slice(0, sourceLineIndex).join('\n').trim();
      } else {
        sourceTag = "NHIS General Guidelines"; 
      }

      setMessages(prev => [...prev, { role: 'agent', text: agentText, source: sourceTag }]);

    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { 
        role: 'agent', 
        text: 'I am currently offline or experiencing a connection error. Please try again later or contact NHIS directly on 0800-900-9900.',
        source: 'System Diagnostic'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 flex flex-row h-[80vh] overflow-hidden shadow-sm animate-in fade-in duration-300 relative">
      
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div className="absolute inset-0 bg-black/20 z-20 md:hidden" onClick={() => setSidebarOpen(false)}></div>
      )}

      {/* Left Sidebar (History) */}
      <div className={`absolute md:relative z-30 w-64 h-full bg-slate-50 border-r border-slate-100 flex flex-col transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="p-5 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <h3 className="font-bold text-slate-800">History</h3>
          <button onClick={() => setSidebarOpen(false)} className="md:hidden text-slate-400 hover:text-slate-800">
            <X size={20} />
          </button>
        </div>
        
        <div className="p-3">
          <button className="w-full flex items-center justify-center gap-2 bg-white border border-slate-200 text-[#3454D1] py-2 rounded-lg font-semibold text-sm hover:bg-blue-50 transition-colors shadow-sm mb-4">
            <Plus size={16} /> New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 px-2">Recent</p>
          <div className="flex flex-col gap-1">
            {mockHistory.map(hist => (
              <div key={hist.id} className="px-3 py-2.5 rounded-lg hover:bg-slate-200 cursor-pointer transition-colors group">
                <p className="text-sm font-semibold text-slate-700 truncate group-hover:text-[#3454D1]">{hist.title}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">{hist.date}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-white relative">
        {/* Chat Header */}
        <div className="border-b border-slate-100 p-4 bg-white flex items-center gap-4 shrink-0">
          <button onClick={() => setSidebarOpen(true)} className="md:hidden p-2 -ml-2 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-50">
            <Menu size={20} />
          </button>
          
          <div className="w-10 h-10 md:w-12 md:h-12 bg-blue-50 rounded-xl flex items-center justify-center shrink-0">
            <MessageSquare size={20} className="text-[#3454D1]" />
          </div>
          <div>
            <h2 className="font-bold text-slate-800 text-base md:text-lg">NHIS Policy Agent</h2>
            <p className="text-[11px] md:text-xs text-emerald-600 font-medium flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 block"></span>
              Grounded in Official Policy
            </p>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-grow overflow-y-auto p-4 md:p-6 flex flex-col gap-6 bg-slate-50/30">
          {messages.map((msg, index) => (
            <div key={index} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`
                max-w-[90%] md:max-w-[75%] p-4 text-sm md:text-base leading-relaxed rounded-2xl
                ${msg.role === 'user' 
                  ? 'bg-[#3454D1] text-white rounded-br-sm shadow-sm' 
                  : 'bg-white border border-slate-200 text-slate-800 shadow-sm rounded-bl-sm'}
              `}>
                {msg.text}
              </div>
              
              {msg.role === 'agent' && msg.source && (
                <div className="mt-2 text-[11px] md:text-xs font-medium text-slate-500 flex items-center gap-1 ml-1 bg-white border border-slate-100 px-2.5 py-1 rounded-md shadow-sm">
                  <FileText size={12} className="text-[#3454D1]" />
                  Source: {msg.source}
                </div>
              )}

              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {msg.suggestions.map((suggestion, idx) => (
                    <button 
                      key={idx}
                      onClick={() => handleSend(null, suggestion)}
                      className="text-xs font-medium border border-slate-200 bg-white text-slate-600 px-4 py-2.5 rounded-full hover:border-[#3454D1] hover:text-[#3454D1] hover:shadow-sm transition-all"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="flex items-start">
              <div className="bg-white border border-slate-200 text-slate-500 rounded-2xl rounded-bl-sm p-4 text-sm font-medium flex items-center gap-3 shadow-sm">
                <div className="flex gap-1.5">
                  <span className="w-1.5 h-1.5 bg-[#3454D1] rounded-full animate-bounce"></span>
                  <span className="w-1.5 h-1.5 bg-[#3454D1] rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></span>
                  <span className="w-1.5 h-1.5 bg-[#3454D1] rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
                </div>
                Searching knowledge base...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-200 p-4 bg-white shrink-0">
          <form onSubmit={handleSend} className="flex gap-3">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question about NHIS policy..."
              className="flex-grow border border-slate-200 rounded-xl p-3.5 focus:outline-none focus:ring-2 focus:ring-[#3454D1] focus:border-transparent text-slate-800 text-sm shadow-sm"
              disabled={isLoading}
            />
            <button 
              type="submit" 
              disabled={isLoading || !input.trim()}
              className="bg-[#3454D1] text-white px-5 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-[#3454D1] transition-colors flex items-center justify-center shadow-sm"
            >
              <Send size={18} />
              <span className="sr-only">Send</span>
            </button>
          </form>
        </div>
      </div>

    </div>
  );
}