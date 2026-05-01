import React, { useState, useEffect } from 'react'
import { BookOpen, Clock, ChevronRight, X } from 'lucide-react'
import { resourcesApi } from '../api/resources.js'
import { useLanguage } from '../context/LanguageContext.jsx'

export default function ResourcesPage() {
  const { t } = useLanguage()
  const [resources, setResources] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    resourcesApi.list()
      .then(setResources)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (selected) {
    return (
      <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm">
        <button onClick={() => setSelected(null)} className="flex items-center gap-2 text-[#3454D1] text-sm font-semibold mb-6 hover:underline">
          <X size={16} /> {t('resources.back')}
        </button>
        <div className="max-w-2xl">
          <span className="text-xs font-bold text-[#3454D1] bg-blue-50 px-2.5 py-1 rounded-md">{selected.category}</span>
          <h1 className="text-2xl font-bold text-slate-800 mt-4 mb-2">{selected.title}</h1>
          <p className="text-xs text-slate-400 mb-8 flex items-center gap-1">
            <Clock size={12} /> {selected.read_time} {t('resources.read')}
          </p>
          <div className="prose prose-slate max-w-none text-slate-700 leading-relaxed whitespace-pre-wrap text-sm">
            {selected.content || t('resources.noContent')}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">{t('resources.title2')}</h1>
        <p className="text-slate-500 mt-1 text-sm">{t('resources.subtitle2')}</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <p className="text-slate-400">{t('common.loading')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {resources.map(resource => (
            <div key={resource.id}
              onClick={() => setSelected(resource)}
              className="border border-slate-100 rounded-xl p-6 flex flex-col justify-between hover:border-slate-200 hover:shadow-md transition-all cursor-pointer group bg-slate-50/50">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold text-[#3454D1] bg-blue-50 px-2.5 py-1 rounded-md">{resource.category}</span>
                  <BookOpen size={16} className="text-slate-300" />
                </div>
                <h3 className="font-bold text-lg text-slate-800 mb-2 group-hover:text-[#3454D1] transition-colors leading-snug">{resource.title}</h3>
              </div>
              <div className="flex justify-between items-center mt-8 pt-4 border-t border-slate-100">
                <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
                  <Clock size={14} />{resource.read_time} {t('resources.read')}
                </span>
                <ChevronRight size={18} className="text-slate-300 group-hover:text-[#3454D1] transition-colors" />
              </div>
            </div>
          ))}
          {resources.length === 0 && (
            <div className="col-span-3 text-center py-12 text-slate-400">{t('resources.empty')}</div>
          )}
        </div>
      )}
    </div>
  )
}
