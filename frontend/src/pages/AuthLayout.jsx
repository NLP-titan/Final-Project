import React, { useState } from 'react'
import { ShieldCheck, Eye, EyeOff, Globe } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { LANGUAGES } from '../i18n/strings.js'

const regions = ["Greater Accra", "Ashanti", "Central", "Western", "Eastern", "Northern", "Volta", "Upper East", "Upper West", "Oti", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Western North"]

export default function AuthLayout({ currentPage, navigateTo }) {
  return (
    <div className="min-h-screen md:h-screen w-full bg-white font-sans flex">
      <div className="w-full h-full flex flex-col md:flex-row">

        {/* Left Panel */}
        <div className="w-full md:w-1/2 flex flex-col min-h-[40vh] md:min-h-0 md:h-full border-r border-slate-100 shrink-0">
          <div
            className="h-[40vh] md:h-[55%] w-full bg-cover bg-center bg-no-repeat shrink-0"
            style={{ backgroundImage: "url('/dr.jpg')" }}
          />
          <div className="flex-1 bg-[#3454D1] text-white p-8 md:p-12 lg:p-16 flex flex-col justify-center">
            <div className="flex items-center gap-3 mb-8">
              <ShieldCheck size={28} strokeWidth={2.5} />
              <span className="font-bold text-2xl tracking-wide">NHIS Agent</span>
            </div>
            <div className="flex">
              <div className="w-1 bg-white mr-5 mt-1 rounded-full shrink-0" />
              <div>
                <h1 className="text-[22px] md:text-2xl font-normal leading-snug mb-3">
                  Welcome to <span className="font-bold">NHIS Agent</span><br />
                  <span className="font-bold">Patient Rights &amp; Entitlement</span>
                </h1>
                <p className="text-blue-100/90 text-[13px] leading-relaxed max-w-sm">
                  Understand your coverage, find accredited facilities, and navigate your healthcare rights — grounded in official NHIS policy.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-full md:w-1/2 p-8 md:p-12 lg:p-16 flex items-center justify-center bg-white h-full overflow-y-auto">
          <div className="w-full max-w-[400px] mx-auto py-8">
            <div className="flex items-center gap-3 mb-10 text-[#3454D1]">
              <ShieldCheck size={32} strokeWidth={2.5} />
              <span className="font-bold text-2xl tracking-wide">NHIS Agent</span>
            </div>

            {currentPage === 'landing' && <LandingPanel navigateTo={navigateTo} />}
            {currentPage === 'login' && <LoginPanel navigateTo={navigateTo} />}
            {currentPage === 'signup' && <SignupPanel navigateTo={navigateTo} />}
          </div>
        </div>
      </div>
    </div>
  )
}

function LandingPanel({ navigateTo }) {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-[32px] font-bold text-slate-800 mb-1">Welcome</h2>
      <p className="text-[15px] font-medium text-slate-600 mb-6">
        Know your NHIS rights. Ask anything. Get answers grounded in official policy.
      </p>
      <button onClick={() => navigateTo('login')} className="w-full bg-[#3454D1] text-white rounded-lg py-3.5 font-semibold hover:bg-blue-700 transition-colors">
        Sign In
      </button>
      <button onClick={() => navigateTo('signup')} className="w-full bg-slate-50 text-[#3454D1] rounded-lg py-3.5 font-semibold hover:bg-slate-100 transition-colors border border-slate-200">
        Create an Account
      </button>
    </div>
  )
}

function LoginPanel({ navigateTo }) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigateTo('dashboard')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col">
      <h2 className="text-[32px] font-bold text-slate-800 mb-1">Login</h2>
      <p className="text-[15px] font-medium text-slate-600 mb-8">Enter your credentials to access your account</p>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <label className="text-[13px] font-bold text-slate-800">Email</label>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
            className="border border-slate-200 rounded-lg p-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] focus:border-[#3454D1]" />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[13px] font-bold text-slate-800">Password</label>
          <div className="relative">
            <input type={showPw ? 'text' : 'password'} required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full border border-slate-200 rounded-lg p-3.5 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1] focus:border-[#3454D1] pr-12" />
            <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-4 top-4 text-slate-300 hover:text-slate-500">
              {showPw ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading}
          className="w-full bg-[#3454D1] text-white rounded-lg py-3.5 font-semibold hover:bg-blue-700 transition-colors mt-2 disabled:opacity-60">
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
      <p className="mt-8 text-[14px] text-slate-800 font-medium text-center">
        Don't have an account?{' '}
        <span onClick={() => navigateTo('signup')} className="font-semibold text-[#3454D1] cursor-pointer hover:underline">Sign Up</span>
      </p>
    </div>
  )
}

function SignupPanel({ navigateTo }) {
  const { register } = useAuth()
  const [form, setForm] = useState({ fullName: '', email: '', phone: '', region: 'Greater Accra', nhisNumber: '', membershipType: 'Standard', password: '', language: 'en' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register({
        email: form.email,
        password: form.password,
        full_name: form.fullName,
        phone: form.phone || undefined,
        region: form.region || undefined,
        nhis_number: form.nhisNumber || undefined,
        membership_type: form.membershipType || undefined,
        language_preference: form.language || 'en',
      })
      navigateTo('dashboard')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const cls = "border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]"

  return (
    <div className="flex flex-col">
      <h2 className="text-[32px] font-bold text-slate-800 mb-1">Sign Up</h2>
      <p className="text-[15px] font-medium text-slate-600 mb-6">Create an account to track your NHIS benefits</p>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] font-bold text-slate-800">Full Name</label>
          <input type="text" required placeholder="e.g. Kwame Mensah" value={form.fullName} onChange={set('fullName')} className={cls} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] font-bold text-slate-800">Email Address</label>
          <input type="email" required placeholder="kwame@example.com" value={form.email} onChange={set('email')} className={cls} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-slate-800">Phone (Optional)</label>
            <input type="tel" placeholder="054 123 4567" value={form.phone} onChange={set('phone')} className={cls} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-slate-800">Region</label>
            <select value={form.region} onChange={set('region')} className={`${cls} bg-white`}>
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-slate-800">NHIS Number</label>
            <input type="text" placeholder="8 digit number" value={form.nhisNumber} onChange={set('nhisNumber')} className={cls} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[13px] font-bold text-slate-800">Membership</label>
            <select value={form.membershipType} onChange={set('membershipType')} className={`${cls} bg-white`}>
              <option value="Standard">Standard</option>
              <option value="Informal">Informal</option>
              <option value="SSNIT">SSNIT</option>
              <option value="Indigent">Indigent</option>
            </select>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] font-bold text-slate-800 flex items-center gap-1.5">
            <Globe size={14} className="text-[#3454D1]" /> Preferred Language
          </label>
          <p className="text-[11px] text-slate-500 -mt-0.5">The agent will reply in this language and key labels will be translated.</p>
          <div className="grid grid-cols-2 gap-2 mt-1">
            {LANGUAGES.map(l => (
              <button type="button" key={l.code}
                onClick={() => setForm(f => ({ ...f, language: l.code }))}
                className={`p-2.5 rounded-lg border text-sm font-semibold transition-all ${form.language === l.code ? 'bg-blue-50 border-[#3454D1] text-[#3454D1] ring-2 ring-[#3454D1]/20' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}>
                {l.nativeLabel}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-[13px] font-bold text-slate-800">Password</label>
          <input type="password" required minLength={8} placeholder="Minimum 8 characters" value={form.password} onChange={set('password')} className={cls} />
        </div>
        <button type="submit" disabled={loading}
          className="w-full bg-[#3454D1] text-white rounded-lg py-3.5 font-semibold hover:bg-blue-700 transition-colors mt-4 disabled:opacity-60">
          {loading ? 'Creating account...' : 'Create Account'}
        </button>
      </form>
      <p className="mt-6 text-[14px] text-slate-800 font-medium text-center">
        Already have an account?{' '}
        <span onClick={() => navigateTo('login')} className="font-semibold text-[#3454D1] cursor-pointer hover:underline">Log In</span>
      </p>
    </div>
  )
}
