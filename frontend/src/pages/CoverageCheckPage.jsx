import React, { useState } from 'react'
import { Upload, FileText, Pill, CheckCircle2, XCircle, AlertTriangle, Loader2, Camera } from 'lucide-react'
import { prescriptionsApi, medicinesIdentifyApi } from '../api/prescriptions.js'
import { useLanguage } from '../context/LanguageContext.jsx'

const MODE_DEFS = [
  { id: 'prescription', labelKey: 'coverage.modePrescription', helperKey: 'coverage.helperPrescription', icon: FileText },
  { id: 'drug', labelKey: 'coverage.modeDrug', helperKey: 'coverage.helperDrug', icon: Pill },
]

const ACCEPT_TYPES = 'image/png,image/jpeg,image/webp,image/gif,application/pdf'
const MAX_MB = 8

export default function CoverageCheckPage() {
  const { t } = useLanguage()
  const [mode, setMode] = useState('prescription')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const reset = () => {
    setFile(null); setPreview(null); setResult(null); setError(null)
  }

  const onPickFile = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File is too large. Maximum is ${MAX_MB} MB.`)
      return
    }
    setError(null); setResult(null); setFile(f)
    if (f.type.startsWith('image/')) {
      const url = URL.createObjectURL(f)
      setPreview(url)
    } else {
      setPreview(null)
    }
  }

  const onSubmit = async () => {
    if (!file) return
    setSubmitting(true); setError(null); setResult(null)
    try {
      const data = mode === 'prescription'
        ? await prescriptionsApi.analyze(file)
        : await medicinesIdentifyApi.identify(file)
      setResult(data)
    } catch (e) {
      setError(e.message || 'Analysis failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm flex flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">{t('coverage.title')}</h1>
        <p className="text-slate-500 mt-1 text-sm">{t('coverage.subtitle')}</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        {MODE_DEFS.map(m => {
          const Icon = m.icon
          const active = mode === m.id
          return (
            <button key={m.id} onClick={() => { setMode(m.id); reset() }}
              className={`flex-1 flex items-start gap-3 p-4 rounded-xl border text-left transition-all ${active ? 'bg-blue-50 border-[#3454D1] ring-2 ring-[#3454D1]/20' : 'bg-white border-slate-200 hover:border-slate-300'}`}>
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${active ? 'bg-[#3454D1] text-white' : 'bg-slate-100 text-slate-500'}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className={`font-semibold ${active ? 'text-[#3454D1]' : 'text-slate-800'}`}>{t(m.labelKey)}</p>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">{t(m.helperKey)}</p>
              </div>
            </button>
          )
        })}
      </div>

      {/* Uploader */}
      <div className="border-2 border-dashed border-slate-200 rounded-xl p-6 mb-6 bg-slate-50/40">
        <label className="flex flex-col items-center justify-center cursor-pointer text-center py-6 hover:opacity-80 transition-opacity">
          <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mb-3 text-[#3454D1]">
            {mode === 'prescription' ? <Upload size={24} /> : <Camera size={24} />}
          </div>
          <p className="font-semibold text-slate-800">{file ? file.name : t('coverage.pickFile')}</p>
          <p className="text-xs text-slate-500 mt-1">{t('coverage.fileLimit')}</p>
          <input type="file" accept={ACCEPT_TYPES} className="hidden" onChange={onPickFile} />
        </label>

        {preview && (
          <div className="mt-4 flex justify-center">
            <img src={preview} alt="Preview" className="max-h-60 rounded-lg border border-slate-200 shadow-sm" />
          </div>
        )}

        {file && (
          <div className="flex justify-center gap-3 mt-4">
            <button onClick={onSubmit} disabled={submitting}
              className="px-5 py-2.5 rounded-lg bg-[#3454D1] text-white font-semibold text-sm flex items-center gap-2 disabled:opacity-60 hover:bg-[#2a44b1] transition-colors">
              {submitting ? <><Loader2 size={16} className="animate-spin" /> {t('coverage.analysing')}</> : t('coverage.run')}
            </button>
            <button onClick={reset} disabled={submitting}
              className="px-5 py-2.5 rounded-lg bg-white border border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50">
              {t('common.clear')}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 mb-6 flex gap-3">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {result && mode === 'prescription' && <PrescriptionResultView data={result} />}
      {result && mode === 'drug' && <DrugResultView data={result} />}
    </div>
  )
}

function StatusBadge({ status }) {
  const { t } = useLanguage()
  const map = {
    covered: { c: 'bg-emerald-50 text-emerald-700 border-emerald-200', labelKey: 'coverage.covered', icon: CheckCircle2 },
    accredited: { c: 'bg-emerald-50 text-emerald-700 border-emerald-200', labelKey: 'coverage.accredited', icon: CheckCircle2 },
    not_covered: { c: 'bg-red-50 text-red-700 border-red-200', labelKey: 'coverage.notCovered', icon: XCircle },
    not_accredited: { c: 'bg-red-50 text-red-700 border-red-200', labelKey: 'coverage.notAccredited', icon: XCircle },
    not_found: { c: 'bg-amber-50 text-amber-700 border-amber-200', labelKey: 'common.notFound', icon: AlertTriangle },
    not_provided: { c: 'bg-slate-100 text-slate-600 border-slate-200', labelKey: 'common.notProvided', icon: AlertTriangle },
  }
  const m = map[status] || map.not_found
  const Icon = m.icon
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-md border ${m.c}`}>
      <Icon size={14} /> {t(m.labelKey)}
    </span>
  )
}

function PrescriptionResultView({ data }) {
  const { t } = useLanguage()
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-800 mb-2">{t('coverage.summary')}</p>
        <p className="text-sm text-slate-600">{data.summary}</p>
        {data.notes && <p className="text-xs text-slate-400 italic mt-2">{data.notes}</p>}
        {data.confidence && (
          <p className="text-xs text-slate-400 mt-2">{t('common.confidence')}: <span className="font-semibold capitalize">{data.confidence}</span></p>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-800 mb-3">{t('coverage.drugs')}</p>
        {data.drugs.length === 0 && <p className="text-sm text-slate-500">—</p>}
        <div className="space-y-3">
          {data.drugs.map((d, i) => (
            <div key={i} className="border border-slate-100 rounded-lg p-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div>
                <p className="font-semibold text-slate-800">{d.queried_name}</p>
                {d.matched_name && d.matched_name !== d.queried_name && (
                  <p className="text-xs text-slate-500 mt-0.5">Matched: {d.matched_name}{d.generic_name ? ` (${d.generic_name})` : ''}</p>
                )}
                {(d.dosage || d.duration) && (
                  <p className="text-xs text-slate-500 mt-1">{[d.dosage, d.duration].filter(Boolean).join(' • ')}</p>
                )}
                {d.level_of_care?.length > 0 && (
                  <p className="text-xs text-slate-400 mt-1">Available at: {d.level_of_care.join(', ')}</p>
                )}
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-800 mb-3">{t('coverage.facility')}</p>
        {data.facility.status === 'not_provided' && (
          <p className="text-sm text-slate-500">—</p>
        )}
        {data.facility.status !== 'not_provided' && (
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div>
              <p className="font-semibold text-slate-800">{data.facility.matched_name || data.facility.queried_name}</p>
              {data.facility.matched_name && data.facility.queried_name && data.facility.matched_name !== data.facility.queried_name && (
                <p className="text-xs text-slate-500 mt-0.5">Detected as: "{data.facility.queried_name}"</p>
              )}
              <p className="text-xs text-slate-500 mt-1">
                {[data.facility.type, data.facility.region, data.facility.town].filter(Boolean).join(' • ')}
              </p>
            </div>
            <StatusBadge status={data.facility.status} />
          </div>
        )}
      </div>
    </div>
  )
}

function DrugResultView({ data }) {
  const { t } = useLanguage()
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-800 mb-2">{t('coverage.identification')}</p>
        <p className="text-lg font-bold text-slate-900">{data.identified_name || '—'}</p>
        {data.brand && <p className="text-xs text-slate-500 mt-1">{data.brand}</p>}
        {data.dosage_form && <p className="text-xs text-slate-500 mt-1">{data.dosage_form}</p>}
        {data.strength && <p className="text-xs text-slate-500 mt-0.5">{data.strength}</p>}
        {data.confidence && (
          <p className="text-xs text-slate-400 mt-2">{t('common.confidence')}: <span className="font-semibold capitalize">{data.confidence}</span></p>
        )}
        {data.notes && <p className="text-xs text-slate-400 italic mt-2">{data.notes}</p>}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-800 mb-1">{t('coverage.coverage')}</p>
            <p className="font-semibold text-slate-700">{data.coverage.matched_name || '—'}</p>
            {data.coverage.generic_name && (
              <p className="text-xs text-slate-500 mt-0.5">Generic: {data.coverage.generic_name}</p>
            )}
            {data.coverage.level_of_care?.length > 0 && (
              <p className="text-xs text-slate-400 mt-1">Available at: {data.coverage.level_of_care.join(', ')}</p>
            )}
            {data.coverage.notes && <p className="text-xs text-slate-400 mt-1">{data.coverage.notes}</p>}
          </div>
          <StatusBadge status={data.coverage.status} />
        </div>
      </div>
    </div>
  )
}
