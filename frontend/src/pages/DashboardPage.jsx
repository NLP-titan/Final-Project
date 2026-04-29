import React, { useEffect, useState } from 'react'
import { User, MessageSquare, MapPin, AlertCircle, ChevronRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { conversationsApi } from '../api/conversations.js'
import { healthUpdatesApi } from '../api/healthUpdates.js'

function membershipStatus(user) {
  if (!user.nhis_number) return { label: 'Not Enrolled', color: 'text-slate-500', dot: 'bg-slate-400' }
  return { label: 'Active', color: 'text-emerald-600', dot: 'bg-emerald-500' }
}

function estimatedExpiry(user) {
  if (!user.nhis_number) return 'N/A'
  const d = new Date(user.created_at)
  d.setFullYear(d.getFullYear() + 1)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function DashboardPage({ navigateTo }) {
  const { user } = useAuth()
  const [conversations, setConversations] = useState([])
  const [updates, setUpdates] = useState([])
  const status = membershipStatus(user)

  useEffect(() => {
    conversationsApi.list().then(setConversations).catch(() => {})
    healthUpdatesApi.list({ limit: 3 }).then(setUpdates).catch(() => {})
  }, [])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

      {/* Left Column */}
      <div className="lg:col-span-2 flex flex-col gap-6">

        {/* Profile Card */}
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 border-b border-slate-100 pb-6 gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-blue-50 text-[#3454D1] rounded-2xl flex items-center justify-center shrink-0">
                <User size={28} strokeWidth={2.5} />
              </div>
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-xl font-bold text-slate-900">{user.full_name || user.email}</h2>
                  {user.nhis_number && (
                    <span className="text-sm font-medium text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md">
                      ID: {user.nhis_number}
                    </span>
                  )}
                </div>
                <p className="text-slate-500 text-sm mt-1">
                  {user.membership_type || 'Standard'} Member{user.region ? ` • ${user.region}` : ''}
                </p>
              </div>
            </div>
            <button
              onClick={() => navigateTo('resources')}
              className="w-full sm:w-auto bg-[#3454D1] text-white px-6 py-2.5 rounded-xl font-semibold text-sm hover:bg-blue-700 transition-colors shadow-sm">
              Renew Membership
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            <div>
              <p className="text-xs text-slate-400 mb-1">Status</p>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${status.dot}`} />
                <p className={`font-semibold ${status.color}`}>{status.label}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Membership</p>
              <p className="font-semibold text-slate-800">{user.membership_type || 'Standard'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Est. Expiry</p>
              <p className="font-semibold text-slate-800">{estimatedExpiry(user)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 mb-1">Region</p>
              <p className="font-semibold text-slate-800">{user.region || '—'}</p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <h3 className="font-bold text-lg text-slate-800 mb-6">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <QuickAction onClick={() => navigateTo('chat')} icon={<MessageSquare size={20} />} bg="bg-blue-50" text="text-[#3454D1]" title="Ask the Agent" sub="Check drug coverage" hoverBorder="hover:border-[#3454D1]" hoverBg="hover:bg-blue-50/50" />
            <QuickAction onClick={() => navigateTo('facilities')} icon={<MapPin size={20} />} bg="bg-indigo-50" text="text-indigo-600" title="Find Facility" sub="Locate hospitals" hoverBorder="hover:border-indigo-400" hoverBg="hover:bg-indigo-50/50" />
            <QuickAction onClick={() => navigateTo('resources')} icon={<AlertCircle size={20} />} bg="bg-emerald-50" text="text-emerald-600" title="Review Rights" sub="Resolve disputes" hoverBorder="hover:border-emerald-400" hoverBg="hover:bg-emerald-50/50" />
          </div>
        </div>

        {/* Recent Conversations */}
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-lg text-slate-800">Recent Conversations</h3>
            <span onClick={() => navigateTo('chat')} className="text-[#3454D1] text-sm font-semibold cursor-pointer flex items-center gap-1 hover:underline">
              View all <ChevronRight size={14} />
            </span>
          </div>
          {conversations.length === 0 ? (
            <p className="text-sm text-slate-400 py-4">No conversations yet. Ask the agent something!</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-slate-400 text-xs border-b border-slate-100">
                    <th className="pb-3 font-medium w-1/2">Topic</th>
                    <th className="pb-3 font-medium">Messages</th>
                    <th className="pb-3 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {conversations.slice(0, 3).map(conv => (
                    <tr key={conv.id} onClick={() => navigateTo('chat')}
                      className="border-b border-slate-50 hover:bg-slate-50 transition-colors cursor-pointer">
                      <td className="py-4 px-2">
                        <p className="font-semibold text-slate-800 mb-1 truncate max-w-[200px]">{conv.title || 'Untitled'}</p>
                      </td>
                      <td className="py-4 text-sm text-slate-600">{conv.message_count}</td>
                      <td className="py-4 text-sm text-slate-600">
                        {new Date(conv.updated_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Right Column — Updates */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm h-full flex flex-col">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-bold text-lg text-slate-800">Latest Updates</h3>
            <span onClick={() => navigateTo('updates')} className="text-[#3454D1] text-sm font-semibold cursor-pointer flex items-center gap-1 hover:underline">
              See all <ChevronRight size={14} />
            </span>
          </div>
          <div className="flex flex-col gap-6 flex-grow">
            {updates.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Latest</p>
                <div className="relative pl-6 border-l-2 border-[#3454D1]">
                  <div className="absolute w-3 h-3 bg-white border-2 border-[#3454D1] rounded-full -left-[7.5px] top-1" />
                  <h4 className="font-bold text-slate-800 text-sm">{updates[0].title}</h4>
                  <p className="text-sm text-slate-500 mt-1 mb-4">{updates[0].published_date}</p>
                  {updates[0].summary && (
                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                      <p className="text-sm text-slate-600 leading-relaxed line-clamp-3">{updates[0].summary}</p>
                      <div className="flex items-center gap-2 text-xs font-medium border-t border-slate-200 pt-3 mt-3">
                        <p className="text-slate-400">Source</p>
                        <p className="text-slate-800">{updates[0].source}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            {updates.length > 1 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Earlier</p>
                <div className="flex flex-col gap-6">
                  {updates.slice(1).map(u => (
                    <div key={u.id} className="relative pl-6 border-l-2 border-slate-200">
                      <div className="absolute w-3 h-3 bg-slate-200 rounded-full -left-[7px] top-1" />
                      <h4 className="font-semibold text-slate-700 text-sm">{u.title}</h4>
                      <p className="text-sm text-slate-400 mt-1">{u.published_date}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button onClick={() => navigateTo('updates')}
            className="w-full mt-6 py-3 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold rounded-xl transition-colors border border-slate-200 text-sm">
            Go to Health Updates
          </button>
        </div>
      </div>
    </div>
  )
}

function QuickAction({ onClick, icon, bg, text, title, sub, hoverBorder, hoverBg }) {
  return (
    <button onClick={onClick}
      className={`flex flex-col items-center justify-center p-6 border border-slate-100 rounded-2xl ${hoverBorder} ${hoverBg} transition-all group shadow-sm`}>
      <div className={`w-12 h-12 rounded-full ${bg} ${text} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
        {icon}
      </div>
      <span className="font-bold text-slate-800 text-sm">{title}</span>
      <span className="text-xs text-slate-500 mt-1 text-center">{sub}</span>
    </button>
  )
}
