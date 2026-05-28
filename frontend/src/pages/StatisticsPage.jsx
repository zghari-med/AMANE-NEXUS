import { useState, useEffect } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import { BarChart3, AlertCircle, Video, TrendingUp, Download } from 'lucide-react'
import toast from 'react-hot-toast'

const API = 'http://localhost:5000'

const TYPE_COLORS = {
  fall:      '#ef4444',
  crowding:  '#f59e0b',
  abandoned: '#3b82f6',
}
const PIE_COLORS = ['#ef4444', '#f59e0b', '#3b82f6']

export default function StatisticsPage() {
  const { token } = useAuthStore()
  const [stats, setStats]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays]     = useState(7)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => { fetchStats() }, [days])

  const fetchStats = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/analyses/statistics`, { headers })
      const d = await r.json()
      setStats(d)
    } catch { toast.error('Erreur chargement statistiques') }
    finally { setLoading(false) }
  }

  // Données pour graphe en secteurs
  const pieData = stats ? [
    { name: 'Chutes',            value: stats.alerts_by_type?.fall      || 0 },
    { name: 'Attroupements',     value: stats.alerts_by_type?.crowding  || 0 },
    { name: 'Objets abandonnés', value: stats.alerts_by_type?.abandoned || 0 },
  ].filter(d => d.value > 0) : []

  // Données pour graphe en barres par vidéo
  const chartData = stats?.chart_data || []

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Statistiques</h1>
              <p className="text-gray-500 text-sm">Analyses des performances et détections</p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={days}
                onChange={e => setDays(Number(e.target.value))}
                className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={7}>7 derniers jours</option>
                <option value={30}>30 derniers jours</option>
                <option value={90}>90 derniers jours</option>
              </select>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full" />
            </div>
          ) : (
            <>
              {/* KPI cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
                {[
                  { label: 'Total alertes',   value: stats?.total_alerts      || 0, icon: AlertCircle, color: 'text-red-600',    bg: 'bg-red-50' },
                  { label: 'Analyses',        value: stats?.total_analyses    || 0, icon: BarChart3,   color: 'text-blue-600',   bg: 'bg-blue-50' },
                  { label: 'Vidéos',          value: stats?.total_videos      || 0, icon: Video,       color: 'text-purple-600', bg: 'bg-purple-50' },
                  { label: 'Total événements',value: stats?.total_events      || 0, icon: TrendingUp,  color: 'text-green-600',  bg: 'bg-green-50' },
                ].map(({ label, value, icon: Icon, color, bg }) => (
                  <div key={label} className={`${bg} rounded-xl p-5 border border-white shadow-sm`}>
                    <div className="flex items-center gap-3 mb-2">
                      <Icon size={20} className={color} />
                      <p className="text-sm font-medium text-gray-600">{label}</p>
                    </div>
                    <p className={`text-3xl font-bold ${color}`}>{value}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">

                {/* Barres par vidéo */}
                <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Événements par Vidéo</h3>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={chartData} margin={{ left: -10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Legend iconSize={10} />
                        <Bar dataKey="chutes"        name="Chutes"            fill={TYPE_COLORS.fall}      radius={[3,3,0,0]} />
                        <Bar dataKey="attroupements" name="Attroupements"     fill={TYPE_COLORS.crowding}  radius={[3,3,0,0]} />
                        <Bar dataKey="objets"        name="Obj. abandonnés"   fill={TYPE_COLORS.abandoned} radius={[3,3,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-60 text-gray-400 text-sm">
                      Aucune analyse complétée
                    </div>
                  )}
                </div>

                {/* Pie chart */}
                <div className="bg-white rounded-xl shadow-sm border p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Répartition par type</h3>
                  {pieData.length > 0 ? (
                    <>
                      <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                          <Pie data={pieData} cx="50%" cy="50%"
                               innerRadius={50} outerRadius={80}
                               paddingAngle={4} dataKey="value">
                            {pieData.map((_, i) => (
                              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="space-y-2 mt-2">
                        {pieData.map((d, i) => (
                          <div key={d.name} className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rounded-full" style={{ background: PIE_COLORS[i] }} />
                              <span className="text-gray-600">{d.name}</span>
                            </div>
                            <span className="font-semibold">{d.value}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-60 text-gray-400 text-sm">
                      Aucune alerte
                    </div>
                  )}
                </div>
              </div>

              {/* Alertes récentes */}
              {stats?.recent_alerts?.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Alertes Récentes</h3>
                  <div className="divide-y">
                    {stats.recent_alerts.map(al => (
                      <div key={al._id} className="flex items-center gap-4 py-3">
                        <div className="w-2 h-8 rounded-full shrink-0" style={{
                          background: TYPE_COLORS[al.event_type] || '#94a3b8'
                        }} />
                        {al.capture && (
                          <img
                            src={`${API}/api/captures/${al.capture}`}
                            className="w-16 h-12 object-cover rounded"
                            onError={e => { e.target.style.display = 'none' }}
                          />
                        )}
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">
                            {{ fall: 'Chute détectée', crowding: 'Attroupement', abandoned: 'Objet abandonné' }[al.event_type] || al.event_type}
                            {' · '}<span className="text-gray-500">{al.video_title}</span>
                          </p>
                          <p className="text-xs text-gray-400">
                            Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s
                          </p>
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
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
