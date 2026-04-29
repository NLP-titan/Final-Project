import React, { useState, useEffect } from 'react'
import { ShieldCheck, ChevronRight } from 'lucide-react'
import { healthUpdatesApi } from '../api/healthUpdates.js'

const categories = ['All', 'Policy Updates', 'Drug Formulary', 'Disease Alerts', 'General Health']

export default function UpdatesPage() {
  const [updates, setUpdates] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeCategory, setActiveCategory] = useState('All')

  useEffect(() => {
    healthUpdatesApi.list({ category: activeCategory, limit: 20 })
      .then(setUpdates)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [activeCategory])

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm flex flex-col">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Health Updates</h1>
        <p className="text-slate-500 mt-1 text-sm">Curated news, policy changes, and alerts relevant to NHIS subscribers.</p>
      </div>

      <div className="flex flex-wrap gap-2 mb-8">
        {categories.map(cat => (
          <button key={cat} onClick={() => setActiveCategory(cat)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors border ${
              activeCategory === cat ? 'bg-[#3454D1] text-white border-[#3454D1]' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
            }`}>
            {cat}
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
              <div className="sm:w-32 flex shrink-0 items-center justify-start sm:justify-end">
                <button className="text-[#3454D1] text-sm font-semibold hover:underline flex items-center gap-1">
                  Read More <ChevronRight size={16} />
                </button>
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
