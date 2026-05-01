import React, { useState } from 'react'
import { Settings, Bell, Trash2, Globe } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'
import { authApi } from '../api/auth.js'
import { conversationsApi } from '../api/conversations.js'
import { LANGUAGES } from '../i18n/strings.js'

const regions = ["Greater Accra", "Ashanti", "Central", "Western", "Eastern", "Northern", "Volta", "Upper East", "Upper West", "Oti", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Western North"]

export default function ProfilePage({ navigateTo }) {
  const { user, updateUser, logout } = useAuth()
  const { language, setLanguage, isLoading: langLoading, t } = useLanguage()
  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    phone: user?.phone || '',
    region: user?.region || '',
    nhis_number: user?.nhis_number || '',
    membership_type: user?.membership_type || 'Standard',
    language_preference: user?.language_preference || 'en',
  })
  const [notifications, setNotifications] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }))

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const updated = await authApi.updateMe(form)
      updateUser(updated)
      // Sync the in-app language right away so the catalog re-fetches.
      if (form.language_preference && form.language_preference !== language) {
        setLanguage(form.language_preference)
      }
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err.message || 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  const handleClearHistory = async () => {
    if (!confirm(t('profile.clearHistoryConfirm'))) return
    try {
      const convs = await conversationsApi.list()
      await Promise.all(convs.map(c => conversationsApi.delete(c.id)))
    } catch {}
  }

  const cls = "border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#3454D1]"

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm max-w-4xl mx-auto w-full">
      <div className="mb-8 border-b border-slate-100 pb-6 flex items-center gap-4">
        <div className="w-16 h-16 bg-blue-50 text-[#3454D1] rounded-2xl flex items-center justify-center shrink-0">
          <Settings size={32} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t('profile.title')}</h1>
          <p className="text-slate-500 mt-1 text-sm">{t('profile.subtitle')}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">

        {/* Personal Details */}
        <form onSubmit={handleSave} className="flex flex-col gap-6">
          <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2">{t('profile.personalInfo')}</h3>
          {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">{t('profile.fullName')}</label>
              <input type="text" value={form.full_name} onChange={set('full_name')} className={cls} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">{t('profile.email')}</label>
              <input type="email" value={user?.email || ''} disabled className={`${cls} bg-slate-50 text-slate-400`} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">{t('profile.phone')}</label>
              <input type="tel" value={form.phone} onChange={set('phone')} className={cls} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[13px] font-bold text-slate-600">{t('profile.region')}</label>
              <select value={form.region} onChange={set('region')} className={`${cls} bg-white`}>
                <option value="">{t('profile.regionPlaceholder')}</option>
                {regions.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <button type="submit" disabled={saving}
              className={`font-semibold py-3 rounded-lg transition-colors mt-2 text-sm ${saved ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}>
              {saving ? t('profile.saving') : saved ? t('profile.saved') : t('profile.saveChanges')}
            </button>
          </div>
        </form>

        {/* NHIS & Preferences */}
        <div className="flex flex-col gap-10">
          <div className="flex flex-col gap-6">
            <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2">{t('profile.membership')}</h3>
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-slate-500">{t('profile.nhisNumber')}</span>
                <input type="text" value={form.nhis_number} onChange={set('nhis_number')}
                  placeholder={t('profile.nhisNumberPlaceholder')}
                  className="text-right font-semibold text-slate-800 bg-transparent border-none outline-none text-sm w-40" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-slate-500">{t('profile.membershipType')}</span>
                <select value={form.membership_type} onChange={set('membership_type')}
                  className="text-right font-semibold text-slate-800 bg-transparent border-none outline-none text-sm cursor-pointer">
                  <option value="Standard">Standard</option>
                  <option value="Informal">Informal</option>
                  <option value="SSNIT">SSNIT</option>
                  <option value="Indigent">Indigent</option>
                </select>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-bold text-slate-500">{t('profile.accountEmail')}</span>
                <span className="font-semibold text-slate-800 text-sm">{user?.email}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-6">
            <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2 flex items-center gap-2">
              <Globe size={18} className="text-[#3454D1]" /> {t('profile.language')}
            </h3>
            <p className="text-xs text-slate-500 -mt-2">{t('profile.languageHint')}</p>
            <div className="grid grid-cols-2 gap-2">
              {LANGUAGES.map(l => (
                <button type="button" key={l.code}
                  onClick={() => setForm(f => ({ ...f, language_preference: l.code }))}
                  className={`p-3 rounded-lg border text-sm font-semibold transition-all ${form.language_preference === l.code ? 'bg-blue-50 border-[#3454D1] text-[#3454D1] ring-2 ring-[#3454D1]/20' : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'}`}>
                  {l.nativeLabel}
                </button>
              ))}
            </div>
            {langLoading && (
              <p className="text-xs text-slate-400 italic">{t('profile.translating')}</p>
            )}
          </div>

          <div className="flex flex-col gap-6">
            <h3 className="font-bold text-lg text-slate-800 border-b border-slate-100 pb-2">{t('profile.preferences')}</h3>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-50 text-[#3454D1] flex items-center justify-center">
                  <Bell size={18} />
                </div>
                <div>
                  <p className="font-semibold text-slate-800 text-sm">{t('profile.renewalReminders')}</p>
                  <p className="text-xs text-slate-500">{t('profile.renewalRemindersDesc')}</p>
                </div>
              </div>
              <button onClick={() => setNotifications(!notifications)}
                className={`w-12 h-6 rounded-full transition-colors relative ${notifications ? 'bg-[#3454D1]' : 'bg-slate-300'}`}>
                <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${notifications ? 'translate-x-7' : 'translate-x-1'}`} />
              </button>
            </div>
            <div className="flex items-center justify-between border-t border-slate-100 pt-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-red-50 text-red-500 flex items-center justify-center">
                  <Trash2 size={18} />
                </div>
                <div>
                  <p className="font-semibold text-slate-800 text-sm">{t('profile.clearHistory')}</p>
                  <p className="text-xs text-slate-500">{t('profile.clearHistoryDesc')}</p>
                </div>
              </div>
              <button onClick={handleClearHistory} className="text-red-500 text-sm font-semibold hover:underline">{t('common.clear')}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
