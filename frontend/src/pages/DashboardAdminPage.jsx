import { useState, useEffect } from 'react'
import Sidebar from '../components/Sidebar'
import StatCard from '../components/StatCard'
import { Users, Video, BarChart3, AlertCircle, Camera, Clock } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import {
  RadialBarChart, RadialBar, ResponsiveContainer, Tooltip,
} from 'recharts'

import { API, captureUrl } from '../services/api'

const EVENT_LABELS = {
  fall:      'Chute détectée',
  crowding:  'Attroupement',
  abandoned: 'Objet abandonné',
}
const RISK_COLORS = {
  high:   'bg-red-500',
  medium: 'bg-yellow-500',
  low:    'bg-blue-400',
}

export default function DashboardAdminPage() {
  const { token, user } = useAuthStore()
  const capture = (f) => captureUrl(f, token)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // auto-refresh toutes les 30s
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` }
      const r = await fetch(`${API}/api/analyses/statistics`, { headers })
      const d = await r.json()
      setStats(d)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  const total = (stats?.alerts_by_type?.fall || 0)
              + (stats?.alerts_by_type?.crowding || 0)
              + (stats?.alerts_by_type?.abandoned || 0)

  const pct = (n) => total > 0 ? Math.round((n / total) * 100) : 0

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5">
            <h1 className="text-2xl font-bold text-gray-900">Tableau de Bord</h1>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">

          {/* Stat cards */}
          <div className={`grid gap-5 mb-8 ${isAdmin ? 'grid-cols-2 lg:grid-cols-4' : 'grid-cols-1 sm:grid-cols-3'}`}>
            {isAdmin && (
              <StatCard title="Utilisateurs"    value={loading ? '…' : (stats?.total_users ?? 0)}    icon={Users}       color="blue"   />
            )}
            <StatCard title="Vidéos"            value={loading ? '…' : (stats?.total_videos ?? 0)}   icon={Video}       color="purple" />
            <StatCard title="Analyses"          value={loading ? '…' : (stats?.total_analyses ?? 0)} icon={BarChart3}   color="green"  />
            <StatCard title="Alertes totales"   value={loading ? '…' : (stats?.total_alerts ?? 0)}   icon={AlertCircle} color="red"    />
          </div>

          <div className="grid grid-cols-1 gap-6 mb-8">

            {/* Radial chart — detection breakdown (full width) */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-base font-semibold text-gray-900 mb-1">Répartition des Détections</h3>
              <p className="text-xs text-gray-500 mb-4">Volume d'alertes par catégorie</p>
              {total > 0 ? (() => {
                const radialData = [
                  { name: 'Obj. abandonnés', value: stats?.alerts_by_type?.abandoned || 0, fill: '#3b82f6' },
                  { name: 'Attroupements',   value: stats?.alerts_by_type?.crowding  || 0, fill: '#f59e0b' },
                  { name: 'Chutes',          value: stats?.alerts_by_type?.fall      || 0, fill: '#ef4444' },
                ]
                return (
                  <div className="flex items-center gap-6">
                    <ResponsiveContainer width="55%" height={240}>
                      <RadialBarChart
                        cx="50%" cy="50%"
                        innerRadius={40} outerRadius={100}
                        barSize={18}
                        data={radialData}
                        startAngle={90} endAngle={-270}
                      >
                        <RadialBar dataKey="value" cornerRadius={6} background={{ fill: '#f1f5f9' }} />
                        <Tooltip formatter={(v, n) => [v, n]} />
                      </RadialBarChart>
                    </ResponsiveContainer>
                    <div className="flex-1 space-y-4">
                      {[
                        { key: 'fall',      label: 'Chutes',            color: 'bg-red-500',    text: 'text-red-600' },
                        { key: 'crowding',  label: 'Attroupements',     color: 'bg-yellow-500', text: 'text-yellow-600' },
                        { key: 'abandoned', label: 'Obj. abandonnés',   color: 'bg-blue-500',   text: 'text-blue-600' },
                      ].map(({ key, label, color, text }) => {
                        const n = stats?.alerts_by_type?.[key] ?? 0
                        const p = pct(n)
                        return (
                          <div key={key}>
                            <div className="flex justify-between text-sm mb-1.5">
                              <span className="text-gray-700 font-medium">{label}</span>
                              <span className={`font-bold ${text}`}>{n} <span className="text-gray-400 font-normal text-xs">({p}%)</span></span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-2.5">
                              <div className={`${color} h-2.5 rounded-full transition-all duration-700`}
                                   style={{ width: `${p}%` }} />
                            </div>
                          </div>
                        )
                      })}
                      <div className="pt-3 border-t text-sm flex justify-between items-center">
                        <span className="text-gray-500">Total alertes</span>
                        <span className="text-2xl font-bold text-gray-900">{total}</span>
                      </div>
                    </div>
                  </div>
                )
              })() : (
                <div className="h-60 flex items-center justify-center text-gray-400 text-sm">
                  {loading ? 'Chargement…' : 'Aucune alerte enregistrée'}
                </div>
              )}
            </div>

          </div>

          {/* Recent alerts — with datetime + cam + capture */}
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Alertes Récentes</h3>
            {loading ? (
              <div className="py-8 text-center text-gray-400 text-sm">Chargement…</div>
            ) : stats?.recent_alerts?.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.recent_alerts.map(al => {
                  const dt = al.created_at ? new Date(al.created_at) : null
                  const dateStr = dt && !isNaN(dt)
                    ? dt.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' })
                    : '—'
                  const timeStr = dt && !isNaN(dt)
                    ? dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                    : ''
                  const riskStyle =
                    al.risk_level === 'high'   ? { badge: 'bg-red-100 text-red-700',    border: 'border-red-400',    dot: 'bg-red-500' } :
                    al.risk_level === 'medium' ? { badge: 'bg-yellow-100 text-yellow-700', border: 'border-yellow-400', dot: 'bg-yellow-500' } :
                                                  { badge: 'bg-blue-100 text-blue-700',   border: 'border-blue-300',   dot: 'bg-blue-400' }
                  return (
                    <div key={al._id} className={`rounded-xl border-l-4 ${riskStyle.border} shadow-sm overflow-hidden bg-white`}>
                      {/* Capture image */}
                      {al.capture ? (
                        <div className="relative">
                          <img
                            src={capture(al.capture)}
                            alt={al.event_type}
                            className="w-full h-32 object-cover"
                            onError={e => { e.target.parentElement.style.display = 'none' }}
                          />
                          <span className={`absolute top-2 right-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${riskStyle.badge}`}>
                            {al.risk_level?.toUpperCase()}
                          </span>
                        </div>
                      ) : (
                        <div className="h-20 bg-gray-100 flex items-center justify-center">
                          <AlertCircle size={28} className="text-gray-300" />
                        </div>
                      )}
                      {/* Info */}
                      <div className="p-3 space-y-1.5">
                        <p className="text-sm font-semibold text-gray-900 leading-tight">
                          {EVENT_LABELS[al.event_type] ?? al.event_type}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Camera size={11} />
                          <span className="truncate">{al.video_title}</span>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-400">
                          <Clock size={11} />
                          <span>{dateStr} {timeStr}</span>
                        </div>
                        <p className="text-[10px] text-gray-400">Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="py-8 text-center text-gray-400 text-sm">
                <AlertCircle size={32} className="mx-auto mb-2 opacity-30" />
                Aucune alerte enregistrée
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
