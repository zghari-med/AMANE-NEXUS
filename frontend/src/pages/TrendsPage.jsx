import { useState, useEffect, useCallback } from 'react'
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react'
import toast from 'react-hot-toast'

const API = 'http://localhost:5000'

const TREND_ICON = {
  hausse:  { icon: TrendingUp,   color: 'text-red-500',    bg: 'bg-red-50'   },
  baisse:  { icon: TrendingDown, color: 'text-green-500',  bg: 'bg-green-50' },
  stable:  { icon: Minus,        color: 'text-gray-500',   bg: 'bg-gray-50'  },
}

const TYPE_COLORS = {
  fall:      '#ef4444',
  crowding:  '#f59e0b',
  abandoned: '#3b82f6',
}

export default function TrendsPage() {
  const { token } = useAuthStore()
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [weeks, setWeeks]   = useState(8)

  const headers = { Authorization: `Bearer ${token}` }

  const fetchTrends = useCallback(async () => {
    setLoading(true)
    try {
      // On passe un analysis_id fictif car l'endpoint filtre sur l'user_id
      const r = await fetch(
        `${API}/api/analyses/dummy/trends?weeks=${weeks}`,
        { headers }
      )
      if (!r.ok) throw new Error('Erreur réseau')
      const d = await r.json()
      setData(d)
    } catch (e) {
      toast.error('Erreur chargement tendances : ' + e.message)
    } finally {
      setLoading(false)
    }
  }, [weeks, token])

  useEffect(() => { fetchTrends() }, [fetchTrends])

  // Préparer les données pour le graphe de tendance
  const weeklyData = data?.weekly_data || []
  const eventTypes = weeklyData.length > 0
    ? Object.keys(weeklyData[0]).filter(k => k !== 'week_label')
    : []

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Tendances</h1>
              <p className="text-gray-500 text-sm">Évolution hebdomadaire des détections</p>
            </div>
            <select
              value={weeks}
              onChange={e => setWeeks(Number(e.target.value))}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={4}>4 dernières semaines</option>
              <option value={8}>8 dernières semaines</option>
              <option value={12}>12 dernières semaines</option>
            </select>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full" />
            </div>
          ) : (
            <>
              {/* Indicateurs de tendance */}
              {data?.trends && Object.keys(data.trends).length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
                  {Object.entries(data.trends).map(([type, trend]) => {
                    const cfg = TREND_ICON[trend.direction] ?? TREND_ICON.stable
                    const Icon = cfg.icon
                    const label = {
                      fall: 'Chutes', crowding: 'Attroupements', abandoned: 'Objets abandonnés'
                    }[type] || type
                    return (
                      <div key={type} className={`${cfg.bg} rounded-xl p-5 border border-white shadow-sm`}>
                        <div className="flex items-center gap-3 mb-3">
                          <Icon size={22} className={cfg.color} />
                          <span className="font-semibold text-gray-800">{label}</span>
                        </div>
                        <p className={`text-lg font-bold capitalize ${cfg.color}`}>
                          {trend.direction}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Pente : {trend.slope > 0 ? '+' : ''}{trend.slope} alertes/semaine
                        </p>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Graphe aire — tendances par semaine */}
              <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Activity size={18} className="text-blue-500" />
                  Alertes par semaine ISO
                </h3>
                {weeklyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={weeklyData} margin={{ left: -10, right: 10 }}>
                      <defs>
                        {eventTypes.map((et, i) => (
                          <linearGradient key={et} id={`grad_${et}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor={Object.values(TYPE_COLORS)[i % 3]} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={Object.values(TYPE_COLORS)[i % 3]} stopOpacity={0} />
                          </linearGradient>
                        ))}
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="week_label" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend iconSize={10} />
                      {eventTypes.map((et, i) => {
                        const color = Object.values(TYPE_COLORS)[i % 3]
                        const name  = { fall: 'Chutes', crowding: 'Attroupements', abandoned: 'Obj. abandonnés' }[et] || et
                        return (
                          <Area key={et} type="monotone" dataKey={et} name={name}
                                stroke={color} fill={`url(#grad_${et})`}
                                strokeWidth={2} dot={{ r: 4 }} />
                        )
                      })}
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-60 text-gray-400 text-sm">
                    Pas encore de données de tendance
                    <br />
                    Lancez des analyses pour voir l'évolution
                  </div>
                )}
              </div>

              {/* Résumé total */}
              <div className="bg-white rounded-xl shadow-sm border p-5">
                <h3 className="font-semibold text-gray-900 mb-2">Résumé de la période</h3>
                <div className="flex gap-8 text-sm text-gray-600 mt-3">
                  <div>
                    <span className="text-2xl font-bold text-gray-900">{data?.total_alerts ?? 0}</span>
                    <p className="text-xs mt-0.5">alertes totales</p>
                  </div>
                  <div>
                    <span className="text-2xl font-bold text-gray-900">{weeks}</span>
                    <p className="text-xs mt-0.5">semaines analysées</p>
                  </div>
                  <div>
                    <span className="text-2xl font-bold text-gray-900">
                      {data?.total_alerts && weeks
                        ? (data.total_alerts / weeks).toFixed(1)
                        : '0.0'}
                    </span>
                    <p className="text-xs mt-0.5">alertes/semaine en moy.</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
