import React, { useState, useEffect } from 'react'
import { ShieldCheck, ChevronRight, RefreshCw, ExternalLink } from 'lucide-react'
import { healthUpdatesApi } from '../api/healthUpdates.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useLanguage } from '../context/LanguageContext.jsx'

// Backend filters by canonical English category names; we map them to UI keys
// so the filter chips can be translated without breaking the API call.
const CATEGORY_DEFS = [
  { value: 'All', key: 'updates.allCategories' },
  { value: 'Policy Updates', key: 'updates.policy' },
  { value: 'Drug Formulary', key: 'updates.formulary' },
  { value: 'Disease Alerts', key: 'updates.alerts' },
  { value: 'General Health', key: 'updates.general' },
]

export default function UpdatesPage() {
  const { user } = useAuth()
  const { t } = useLanguage()
  const [updates, setUpdates] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState('All')
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMsg, setRefreshMsg] = useState(null)

  const load = () => {
    setLoading(true)
    return healthUpdatesApi.list({ category: activeCategory, limit: 20 })
      .then(setUpdates)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [activeCategory])

  const onRefresh = async () => {
    setRefreshing(true); setRefreshMsg(null)
    try {
      const res = await healthUpdatesApi.refresh()
      const total = (res.ghs_found || 0) + (res.myjoy_found || 0) + (res.ghanaweb_found || 0)
      setRefreshMsg(`Pulled ${total} item(s); ${res.inserted} new.`)
      await load()
    } catch (e) {
      setRefreshMsg(e.message || 'Refresh failed.')
    } finally {
      setRefreshing(false)
      setTimeout(() => setRefreshMsg(null), 5000)
    }
  }

  const isAdmin = user?.role === 'admin'

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm flex flex-col">
      <div className="mb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t('updates.title')}</h1>
          <p className="text-slate-500 mt-1 text-sm">{t('updates.subtitle')}</p>
        </div>
        {isAdmin && (
          <div className="flex items-center gap-3">
            {refreshMsg && <span className="text-xs text-slate-500">{refreshMsg}</span>}
            <button onClick={onRefresh} disabled={refreshing}
              className="px-4 py-2 rounded-lg bg-[#3454D1] text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-60 hover:bg-[#2a44b1] transition-colors">
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              {refreshing ? t('updates.refreshing') : t('updates.refresh')}
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORY_DEFS.map(cat => (
          <button key={cat.value} onClick={() => setActiveCategory(cat.value)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors border ${
              activeCategory === cat.value ? 'bg-[#3454D1] text-white border-[#3454D1]' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}>
            {t(cat.key)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex-grow flex items-center justify-center">
          <p className="text-slate-400">Loading updates...</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {updates.map(update => (
            <div key={update.id}
              className="border border-slate-100 rounded-xl p-6 hover:shadow-sm transition-all bg-white flex flex-col sm:flex-row gap-6 group">
              <div className="flex-grow">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#3454D1] bg-blue-50 px-2.5 py-1 rounded-md">
                    {update.category}
                  </span>
                  <span className="text-sm text-slate-400 font-medium">{update.published_date}</span>
                </div>
                <h3 className="text-lg font-bold text-slate-800 mb-2 group-hover:text-[#3454D1] transition-colors">{update.title}</h3>
                {update.summary && (
                  <p className="text-sm text-slate-500 line-clamp-2 mb-4">{update.summary}</p>
                )}
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
                  <ShieldCheck size={14} className="text-emerald-500" />
                  Source: {update.source}
                </div>
              </div>
              <div className="sm:w-36 flex shrink-0 items-center justify-start sm:justify-end">
                {update.source_url ? (
                  <a href={update.source_url} target="_blank" rel="noopener noreferrer"
                    className="text-[#3454D1] text-sm font-semibold hover:underline flex items-center gap-1">
                    {t('common.readMore')} <ExternalLink size={14} />
                  </a>
                ) : (
                  <button className="text-slate-400 text-sm font-semibold flex items-center gap-1 cursor-not-allowed">
                    {t('common.notFound')} <ChevronRight size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
          {updates.length === 0 && (
            <div className="py-12 text-center text-slate-400">
              <p className="font-medium">No updates found in this category.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
