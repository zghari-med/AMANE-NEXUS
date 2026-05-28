import { useState, useEffect } from 'react'
import Sidebar from '../components/Sidebar'
import StatCard from '../components/StatCard'
import { Users, Video, BarChart3, AlertCircle, Activity } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const API = 'http://localhost:5000'

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
  const { token } = useAuthStore()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchData() }, [])

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
            <p className="text-gray-500 text-sm">Vue d'ensemble de la plateforme</p>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">

          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
            <StatCard title="Utilisateurs"       value={loading ? '…' : (stats?.total_users ?? 0)}       icon={Users}       color="blue"   />
            <StatCard title="Vidéos"             value={loading ? '…' : (stats?.total_videos ?? 0)}      icon={Video}       color="purple" />
            <StatCard title="Analyses"           value={loading ? '…' : (stats?.total_analyses ?? 0)}    icon={BarChart3}   color="green"  />
            <StatCard title="Alertes totales"    value={loading ? '…' : (stats?.total_alerts ?? 0)}      icon={AlertCircle} color="red"    />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">

            {/* Bar chart — per video */}
            <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border p-5">
              <h3 className="font-semibold text-gray-900 mb-4">Détections par Vidéo</h3>
              {stats?.chart_data?.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={stats.chart_data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend iconSize={10} />
                    <Bar dataKey="chutes"        fill="#ef4444" name="Chutes"        radius={[3,3,0,0]} />
                    <Bar dataKey="attroupements" fill="#f59e0b" name="Attroupements" radius={[3,3,0,0]} />
                    <Bar dataKey="objets"        fill="#3b82f6" name="Obj. abandonnés" radius={[3,3,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-400 text-sm">
                  {loading ? 'Chargement…' : 'Aucune analyse complétée'}
                </div>
              )}
            </div>

            {/* Breakdown */}
            <div className="bg-white rounded-xl shadow-sm border p-5">
              <h3 className="font-semibold text-gray-900 mb-4">Répartition des alertes</h3>
              <div className="space-y-4">
                {[
                  { key: 'fall',      label: 'Chutes',            color: 'bg-red-500' },
                  { key: 'crowding',  label: 'Attroupements',     color: 'bg-yellow-500' },
                  { key: 'abandoned', label: 'Objets abandonnés', color: 'bg-blue-500' },
                ].map(({ key, label, color }) => {
                  const n = stats?.alerts_by_type?.[key] ?? 0
                  const p = pct(n)
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">{label}</span>
                        <span className="font-semibold">{n}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className={`${color} h-2 rounded-full transition-all duration-500`}
                             style={{ width: `${p}%` }} />
                      </div>
                    </div>
                  )
                })}
                <div className="pt-3 border-t text-sm text-gray-500 flex justify-between">
                  <span>Total événements</span>
                  <span className="font-bold text-gray-900">{stats?.total_events ?? 0}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Recent alerts */}
          <div className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Alertes Récentes</h3>
            {loading ? (
              <div className="py-8 text-center text-gray-400 text-sm">Chargement…</div>
            ) : stats?.recent_alerts?.length > 0 ? (
              <div className="divide-y">
                {stats.recent_alerts.map(al => (
                  <div key={al._id} className="flex items-center gap-4 py-3">
                    <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${RISK_COLORS[al.risk_level] ?? 'bg-gray-400'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">
                        {EVENT_LABELS[al.event_type] ?? al.event_type} — <span className="text-gray-500">{al.video_title}</span>
                      </p>
                      <p className="text-xs text-gray-400">Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s</p>
                    </div>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      al.risk_level === 'high'   ? 'bg-red-100 text-red-700' :
                      al.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                   'bg-blue-100 text-blue-700'
                    }`}>
                      {al.risk_level}
                    </span>
                  </div>
                ))}
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
