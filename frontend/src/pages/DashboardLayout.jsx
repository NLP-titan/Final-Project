import React from 'react'
import { ChevronRight, Settings, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'
import DashboardPage from './DashboardPage.jsx'
import ChatPage from './ChatPage.jsx'
import FacilitiesPage from './FacilitiesPage.jsx'
import UpdatesPage from './UpdatesPage.jsx'
import ResourcesPage from './ResourcesPage.jsx'
import ProfilePage from './ProfilePage.jsx'
import CoverageCheckPage from './CoverageCheckPage.jsx'

const tabIds = [
  { id: 'dashboard', key: 'nav.overview' },
  { id: 'chat', key: 'nav.chat' },
  { id: 'coverage', key: 'nav.coverage' },
  { id: 'facilities', key: 'nav.facilities' },
  { id: 'updates', key: 'nav.updates' },
  { id: 'resources', key: 'nav.resources' },
]

export default function DashboardLayout({ currentPage, navigateTo }) {
  const { user, logout } = useAuth()
  const { t } = useLanguage()

  const handleLogout = async () => {
    await logout()
    navigateTo('landing')
  }

  return (
    <div className="min-h-screen bg-[#DDE5ED] text-slate-800 font-sans pb-10 flex flex-col">
      {/* Header */}
      <div className="bg-white px-6 md:px-12 pt-6 pb-0 rounded-b-3xl border-b border-slate-200 mb-6 shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2 text-slate-500 font-medium">
              <span className="cursor-pointer hover:text-slate-800" onClick={() => navigateTo('dashboard')}>{t('nav.portal')}</span>
              <ChevronRight size={16} />
              <span className="text-slate-900 font-semibold">{user?.full_name || user?.email}</span>
            </div>
            <div className="flex items-center gap-6">
              <button onClick={() => navigateTo('profile')} className="text-slate-500 hover:text-[#3454D1] transition-colors flex items-center gap-2 text-sm font-medium">
                <Settings size={18} />
                <span className="hidden sm:inline">{t('nav.settings')}</span>
              </button>
              <button onClick={handleLogout} className="text-slate-500 hover:text-red-500 transition-colors flex items-center gap-2 text-sm font-medium">
                <LogOut size={18} />
                <span className="hidden sm:inline">{t('nav.logout')}</span>
              </button>
            </div>
          </div>
          <div className="flex overflow-x-auto hide-scrollbar gap-8">
            {tabIds.map(tab => (
              <button key={tab.id} onClick={() => navigateTo(tab.id)}
                className={`pb-4 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${
                  currentPage === tab.id ? 'border-[#3454D1] text-[#3454D1]' : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}>
                {t(tab.key)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 md:px-6 w-full flex-grow flex flex-col">
        {currentPage === 'dashboard' && <DashboardPage navigateTo={navigateTo} />}
        {currentPage === 'chat' && <ChatPage />}
        {currentPage === 'coverage' && <CoverageCheckPage />}
        {currentPage === 'facilities' && <FacilitiesPage />}
        {currentPage === 'updates' && <UpdatesPage />}
        {currentPage === 'resources' && <ResourcesPage />}
        {currentPage === 'profile' && <ProfilePage navigateTo={navigateTo} />}
      </main>
    </div>
  )
}
