import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'
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

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  )
}
