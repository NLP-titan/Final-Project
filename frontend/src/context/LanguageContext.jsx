import React, { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react'
import { STRINGS, LANGUAGES } from '../i18n/strings.js'
import { translationApi } from '../api/translation.js'

const LanguageContext = createContext(null)

const CACHE_VERSION = 'v1'
const cacheKey = (lang) => `nhis_i18n_${CACHE_VERSION}_${lang}`
const PREF_KEY = 'nhis_lang_pref'

export function LanguageProvider({ children, initialLanguage }) {
  const [language, setLanguageState] = useState(() => {
    return initialLanguage || localStorage.getItem(PREF_KEY) || 'en'
  })
  const [catalog, setCatalog] = useState({})
  const [isLoading, setIsLoading] = useState(false)

  // If the prop changes (e.g. user logs in with a different preference),
  // sync over from the prop unless the user has explicitly overridden it
  // in this session.
  useEffect(() => {
    if (initialLanguage && initialLanguage !== language) {
      const explicit = localStorage.getItem(PREF_KEY)
      if (!explicit || explicit === language) {
        setLanguageState(initialLanguage)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialLanguage])

  // Whenever the chosen language changes, load the matching translation
  // catalog. English is the source — no API call. For other languages we
  // check localStorage first; on miss (or if new keys were added), batch-
  // translate via Claude and persist.
  useEffect(() => {
    let cancelled = false

    async function loadCatalog() {
      if (language === 'en') {
        setCatalog({})
        return
      }
      // Try cache first.
      let base = {}
      try {
        const cached = localStorage.getItem(cacheKey(language))
        if (cached) base = JSON.parse(cached)
      } catch {}

      if (!cancelled) setCatalog(base)

      const missing = Object.keys(STRINGS).filter(k => !(k in base))
      if (missing.length === 0) return

      setIsLoading(true)
      try {
        const texts = missing.map(k => STRINGS[k])
        const res = await translationApi.batch({ texts, target_lang: language })
        const filled = { ...base }
        missing.forEach((k, i) => { filled[k] = res.texts[i] })
        if (!cancelled) {
          setCatalog(filled)
          localStorage.setItem(cacheKey(language), JSON.stringify(filled))
        }
      } catch {
        // On failure, keep showing the cached catalog; missing keys fall
        // back to English in `t()`.
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    loadCatalog()
    return () => { cancelled = true }
  }, [language])

  const setLanguage = useCallback((code) => {
    if (!LANGUAGES.find(l => l.code === code)) return
    localStorage.setItem(PREF_KEY, code)
    setLanguageState(code)
  }, [])

  // Translate a known key. Falls back to English if the key has no entry yet
  // or the catalog hasn't loaded.
  const t = useCallback((key, fallback) => {
    if (language === 'en') return STRINGS[key] ?? fallback ?? key
    return catalog[key] ?? STRINGS[key] ?? fallback ?? key
  }, [language, catalog])

  const value = useMemo(() => ({
    language,
    setLanguage,
    t,
    isLoading,
    languages: LANGUAGES,
  }), [language, setLanguage, t, isLoading])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used inside <LanguageProvider>')
  return ctx
}
