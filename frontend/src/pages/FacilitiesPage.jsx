import React, { useState, useEffect } from 'react'
import { Search, Filter, Activity, MapPin, List, Map, Navigation } from 'lucide-react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { facilitiesApi } from '../api/facilities.js'
import { useLanguage } from '../context/LanguageContext.jsx'

// Build a Google Maps "directions to here" URL. Uses lat/lng when present —
// works in any browser and deep-links into Google Maps app on iOS/Android.
function directionsUrl(f) {
  if (f.lat != null && f.lng != null) {
    return `https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lng}`
  }
  // Fall back to a search by name if no coordinates are available.
  const query = encodeURIComponent([f.name, f.town, f.region, 'Ghana'].filter(Boolean).join(', '))
  return `https://www.google.com/maps/search/?api=1&query=${query}`
}

// Fix Leaflet default marker icon
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const regions = ["All Regions", "Greater Accra", "Ashanti", "Central", "Western", "Eastern", "Northern", "Volta", "Upper East", "Upper West", "Oti", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Western North"]
const facilityTypes = ["All Types", "Hospital", "Clinic", "Pharmacy", "Diagnostic Centre", "Health Centre", "Polyclinic"]

// Approximate region centres for map default view
const GHANA_CENTRE = [7.9465, -1.0232]

export default function FacilitiesPage() {
  const { t } = useLanguage()
  const [allFacilities, setAllFacilities] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedRegion, setSelectedRegion] = useState('All Regions')
  const [selectedType, setSelectedType] = useState('All Types')
  const [viewMode, setViewMode] = useState('list')

  useEffect(() => {
    facilitiesApi.list({ limit: 200 })
      .then(setAllFacilities)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = allFacilities.filter(f => {
    const q = searchTerm.toLowerCase()
    const matchSearch = !q || f.name.toLowerCase().includes(q) || (f.town || '').toLowerCase().includes(q) || (f.district || '').toLowerCase().includes(q)
    const matchRegion = selectedRegion === 'All Regions' || (f.region || '').toLowerCase() === selectedRegion.toLowerCase()
    const matchType = selectedType === 'All Types' || (f.type || '').toLowerCase().includes(selectedType.toLowerCase())
    return matchSearch && matchRegion && matchType
  })

  // Only facilities with coords for map (facilities without lat/lng get a dummy position spread across Ghana)
  const mapFacilities = filtered.filter(f => f.lat && f.lng)

  return (
    <div className="bg-white rounded-2xl p-6 md:p-8 border border-slate-100 min-h-[75vh] shadow-sm flex flex-col">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t('facilities.title')}</h1>
          <p className="text-slate-500 mt-1 text-sm">{t('facilities.subtitle')}</p>
        </div>
        <div className="flex bg-slate-100 p-1 rounded-lg self-start md:self-end">
          <button onClick={() => setViewMode('list')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${viewMode === 'list' ? 'bg-white text-[#3454D1] shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            <List size={16} /> {t('facilities.list')}
          </button>
          <button onClick={() => setViewMode('map')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors ${viewMode === 'map' ? 'bg-white text-[#3454D1] shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            <Map size={16} /> {t('facilities.map')}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col lg:flex-row gap-4 mb-8 bg-slate-50 p-4 rounded-xl border border-slate-100">
        <div className="flex-grow flex items-center border border-slate-200 rounded-lg px-3 py-2.5 bg-white focus-within:ring-2 focus-within:ring-[#3454D1]">
          <Search size={18} className="text-slate-400 mr-2 shrink-0" />
          <input type="text" placeholder={t('facilities.searchPlaceholder')}
            className="w-full focus:outline-none bg-transparent text-slate-800 text-sm"
            value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2.5 bg-white shrink-0">
            <Filter size={18} className="text-slate-400 mr-2" />
            <select value={selectedRegion} onChange={e => setSelectedRegion(e.target.value)}
              className="bg-transparent text-slate-800 text-sm focus:outline-none cursor-pointer">
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex items-center border border-slate-200 rounded-lg px-3 py-2.5 bg-white shrink-0">
            <Activity size={18} className="text-slate-400 mr-2" />
            <select value={selectedType} onChange={e => setSelectedType(e.target.value)}
              className="bg-transparent text-slate-800 text-sm focus:outline-none cursor-pointer">
              {facilityTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex-grow flex items-center justify-center">
          <p className="text-slate-400">Loading facilities...</p>
        </div>
      ) : viewMode === 'list' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-grow">
          {filtered.map(facility => (
            <a key={facility.id} href={directionsUrl(facility)} target="_blank" rel="noopener noreferrer"
              className="border border-slate-100 rounded-xl p-5 hover:shadow-md hover:border-[#3454D1]/40 transition-all bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4 group cursor-pointer no-underline">
              <div className="flex items-start gap-4">
                <div className="mt-1 w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 shrink-0 group-hover:bg-[#3454D1] group-hover:text-white transition-colors">
                  <MapPin size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 group-hover:text-[#3454D1] transition-colors">{facility.name}</h3>
                  <p className="text-sm text-slate-500 mt-0.5">{facility.type}{facility.region ? ` • ${facility.region}` : ''}{facility.town ? ` • ${facility.town}` : ''}</p>
                  {facility.phone && <p className="text-xs text-slate-400 mt-1">{facility.phone}</p>}
                  <span className="text-xs font-semibold text-[#3454D1] mt-2 inline-flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Navigation size={12} /> {t('common.getDirections')}
                  </span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2 self-start sm:self-center">
                <span className={`px-3 py-1 text-xs font-semibold rounded-md ${facility.accredited ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}`}>
                  {facility.accreditation_status || (facility.accredited ? 'Accredited' : 'Not Accredited')}
                </span>
              </div>
            </a>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full py-16 text-center text-slate-400 flex flex-col items-center">
              <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4">
                <MapPin size={32} className="text-slate-300" />
              </div>
              <p className="font-medium text-slate-600">{t('facilities.noResults')}</p>
              <button onClick={() => { setSearchTerm(''); setSelectedRegion('All Regions'); setSelectedType('All Types') }}
                className="mt-4 text-[#3454D1] text-sm font-semibold hover:underline">
                {t('facilities.clearFilters')}
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-grow flex flex-col gap-3">
          <div className="flex-grow rounded-xl overflow-hidden border border-slate-200 min-h-[450px] relative">
            <MapContainer center={GHANA_CENTRE} zoom={7} style={{ height: '100%', width: '100%', minHeight: '450px' }} scrollWheelZoom>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {mapFacilities.map(f => (
                <Marker key={f.id} position={[f.lat, f.lng]}>
                  <Popup>
                    <div className="font-sans">
                      <p className="font-bold text-sm">{f.name}</p>
                      <p className="text-xs text-slate-500 mt-1">{f.type}{f.region ? ` • ${f.region}` : ''}{f.town ? ` • ${f.town}` : ''}</p>
                      {f.phone && <p className="text-xs mt-1">{f.phone}</p>}
                      <span className={`inline-block mt-2 text-xs font-semibold px-2 py-0.5 rounded ${f.accredited ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
                        {f.accreditation_status || (f.accredited ? 'Accredited' : 'Not Accredited')}
                      </span>
                      <a href={directionsUrl(f)} target="_blank" rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-[#3454D1] hover:underline">
                        <Navigation size={12} /> {t('common.getDirections')}
                      </a>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
            {mapFacilities.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[1000]">
                <div className="bg-white/95 px-6 py-4 rounded-xl shadow-md text-center max-w-sm pointer-events-auto">
                  <p className="font-medium text-slate-700">No mapped facilities match your filters.</p>
                  <p className="text-xs text-slate-500 mt-1">Try clearing the region/type filters, or run the geocoding script to backfill coordinates.</p>
                </div>
              </div>
            )}
          </div>
          <p className="text-xs text-slate-400 text-center">
            Showing {mapFacilities.length} of {filtered.length} matching facilities on the map.
            {filtered.length - mapFacilities.length > 0 && ` ${filtered.length - mapFacilities.length} have no coordinates yet.`}
          </p>
        </div>
      )}
    </div>
  )
}
