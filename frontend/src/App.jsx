import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
import { LanguageProvider } from './context/LanguageContext.jsx'
import AuthLayout from './pages/AuthLayout.jsx'
import DashboardLayout from './pages/DashboardLayout.jsx'

function Router() {
  const { user } = useAuth()
  const [currentPage, setCurrentPage] = useState(user ? 'dashboard' : 'landing')

  const navigateTo = (page) => setCurrentPage(page)

  if (!user || ['landing', 'login', 'signup'].includes(currentPage)) {
    return (
      <AuthLayout
        currentPage={!user ? currentPage : 'landing'}
        navigateTo={(page) => {
          if (page === 'dashboard') setCurrentPage('dashboard')
          else setCurrentPage(page)
        }}
      />
    )
  }

  return <DashboardLayout currentPage={currentPage} navigateTo={navigateTo} />
}

// Pulls the language preference straight from the logged-in user, so the
// catalog matches what the backend will translate agent answers into.
function LanguageBridge({ children }) {
  const { user } = useAuth()
  return (
    <LanguageProvider initialLanguage={user?.language_preference || 'en'}>
      {children}
    </LanguageProvider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <LanguageBridge>
        <Router />
      </LanguageBridge>
    </AuthProvider>
  )
}
