import { useState, useEffect } from 'react'
import Sidebar from '../components/Sidebar'
import StatCard from '../components/StatCard'
import { Users, Video, BarChart3, AlertCircle, Camera, Clock, PersonStanding, Package } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { API, captureUrl } from '../services/api'

const EVENT_LABELS = {
  fall:      'Chute détectée',
  crowding:  'Attroupement',
  abandoned: 'Objet abandonné',
}

const RISK_STYLES = {
  high:   { badge: 'bg-red-100 text-red-600',      dot: 'bg-red-500'    },
  medium: { badge: 'bg-orange-100 text-orange-600', dot: 'bg-orange-400' },
  low:    { badge: 'bg-brand-100 text-brand-600',   dot: 'bg-brand-500'  },
}

const EVENT_ICONS = {
  fall:      { Icon: PersonStanding, bg: 'bg-red-100',    color: 'text-red-500'    },
  crowding:  { Icon: Users,          bg: 'bg-orange-100', color: 'text-orange-500' },
  abandoned: { Icon: Package,        bg: 'bg-blue-100',   color: 'text-blue-500'   },
}

const FILTERS = [
  { key: 'all',      label: 'Tout',              color: '#6366f1', Icon: null           },
  { key: 'fall',     label: 'Chutes',            color: '#EE5D50', Icon: PersonStanding },
  { key: 'crowding', label: 'Attroupements',     color: '#FFB547', Icon: Users          },
  { key: 'abandoned',label: 'Objets abandonnés', color: '#422AFB', Icon: Package        },
]

const BAR_COLORS = {
  fall:      '#EE5D50',
  crowding:  '#FFB547',
  abandoned: '#422AFB',
}

export default function DashboardAdminPage() {
  const { token, user } = useAuthStore()
  const capture = (f) => captureUrl(f, token)
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter]   = useState('all')
  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
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

  /* Bar chart data */
  const allBars = [
    { name: 'Chutes',           key: 'fall',      value: stats?.alerts_by_type?.fall      || 0 },
    { name: 'Attroupements',    key: 'crowding',  value: stats?.alerts_by_type?.crowding  || 0 },
    { name: 'Obj. abandonnés',  key: 'abandoned', value: stats?.alerts_by_type?.abandoned || 0 },
  ]
  const chartData = filter === 'all' ? allBars : allBars.filter(b => b.key === filter)

  /* Recent alerts filtered */
  const recentFiltered = filter === 'all'
    ? (stats?.recent_alerts || [])
    : (stats?.recent_alerts || []).filter(a => a.event_type === filter)

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white rounded-xl shadow-horizon px-4 py-3 text-sm border-0">
        <p className="font-semibold text-navy-700">{payload[0].name}</p>
        <p className="text-secondaryGray-600">{payload[0].value} alerte{payload[0].value > 1 ? 's' : ''}</p>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-secondaryGray-300 overflow-hidden">
      <Sidebar />

      <div className="flex-1 overflow-y-auto">

        {/* Top bar */}
        <div className="sticky top-0 z-10 bg-white px-8 py-5 border-b border-secondaryGray-200">
          <h1 className="text-2xl font-bold text-navy-700">Tableau de Bord</h1>
        </div>

        <div className="px-8 py-6 space-y-6">

          {/* Stat cards */}
          <div className={`grid gap-5 ${isAdmin ? 'grid-cols-2 lg:grid-cols-4' : 'grid-cols-1 sm:grid-cols-3'}`}>
            {isAdmin && (
              <StatCard title="Utilisateurs"  value={loading ? '—' : (stats?.total_users ?? 0)}    icon={Users}       color="blue"   description="Comptes actifs" />
            )}
            <StatCard title="Vidéos"          value={loading ? '—' : (stats?.total_videos ?? 0)}   icon={Video}       color="purple" description="Analysées" />
            <StatCard title="Analyses"        value={loading ? '—' : (stats?.total_analyses ?? 0)} icon={BarChart3}   color="green"  description="Complétées" />
            <StatCard title="Alertes totales" value={loading ? '—' : (stats?.total_alerts ?? 0)}   icon={AlertCircle} color="red"    description="Détections" />
          </div>

          {/* Bar chart + filtre */}
          <div className="bg-white rounded-2xl shadow-horizon p-6">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-base font-bold text-navy-700">Détections par comportement</h3>
                <p className="text-xs text-secondaryGray-600 mt-0.5">Nombre d'alertes par type d'événement</p>
              </div>

              {/* Filtres */}
              <div className="flex gap-2 flex-wrap">
                {FILTERS.map(f => (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    className={`flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                      filter === f.key
                        ? 'text-white border-transparent shadow-sm'
                        : 'bg-white text-secondaryGray-600 border-secondaryGray-200 hover:border-secondaryGray-400'
                    }`}
                    style={filter === f.key ? { background: f.color, borderColor: f.color } : {}}
                  >
                    {f.Icon && <f.Icon size={13} />}
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {total > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData} barSize={filter === 'all' ? 56 : 80} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F4F7FE" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12, fill: '#707EAE', fontFamily: 'DM Sans' }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#707EAE', fontFamily: 'DM Sans' }}
                    axisLine={false} tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F4F7FE', radius: 8 }} />
                  <Bar dataKey="value" name="Alertes" radius={[8, 8, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.key} fill={BAR_COLORS[entry.key]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-60 flex flex-col items-center justify-center text-secondaryGray-500 text-sm gap-2">
                <AlertCircle size={36} className="opacity-30" />
                {loading ? 'Chargement…' : 'Aucune alerte enregistrée'}
              </div>
            )}

            {/* Légende */}
            {total > 0 && (
              <div className="flex gap-6 mt-4 pt-4 border-t border-secondaryGray-200 flex-wrap">
                {allBars.map(b => {
                  const ev = EVENT_ICONS[b.key]
                  return (
                  <div key={b.key} className="flex items-center gap-2">
                    <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${ev?.bg ?? ''}`}
                         style={!ev ? { background: BAR_COLORS[b.key] + '20' } : {}}>
                      {ev
                        ? <ev.Icon size={13} className={ev.color} />
                        : <div className="w-2.5 h-2.5 rounded-sm" style={{ background: BAR_COLORS[b.key] }} />
                      }
                    </div>
                    <span className="text-xs text-secondaryGray-600">{b.name}</span>
                    <span className="text-xs font-bold text-navy-700">{b.value}</span>
                  </div>
                )})}
                <div className="ml-auto text-xs text-secondaryGray-500">
                  Total : <span className="font-bold text-navy-700">{total}</span>
                </div>
              </div>
            )}
          </div>

          {/* Recent alerts */}
          <div className="bg-white rounded-2xl shadow-horizon p-6">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-base font-bold text-navy-700">Alertes Récentes</h3>
                <p className="text-xs text-secondaryGray-600 mt-0.5">
                  {filter === 'all' ? 'Toutes les détections' : `Filtre : ${FILTERS.find(f => f.key === filter)?.label}`}
                </p>
              </div>
            </div>

            {loading ? (
              <div className="py-10 text-center text-secondaryGray-500 text-sm">Chargement…</div>
            ) : recentFiltered.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {recentFiltered.map(al => {
                  const dt = al.created_at ? new Date(al.created_at) : null
                  const dateStr = dt && !isNaN(dt)
                    ? dt.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' })
                    : '—'
                  const timeStr = dt && !isNaN(dt)
                    ? dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
                    : ''
                  const rs = RISK_STYLES[al.risk_level] ?? RISK_STYLES.low
                  const ev = EVENT_ICONS[al.event_type]

                  return (
                    <div key={al._id} className="bg-secondaryGray-300 rounded-2xl overflow-hidden hover:shadow-horizon transition-all">
                      {/* Capture ou icône */}
                      {al.capture ? (
                        <div className="relative">
                          <img
                            src={capture(al.capture)}
                            alt={al.event_type}
                            className="w-full h-32 object-cover"
                            onError={e => { e.target.parentElement.style.display = 'none' }}
                          />
                          <span className={`absolute top-2 right-2 text-[10px] font-bold px-2 py-0.5 rounded-full ${rs.badge}`}>
                            {al.risk_level?.toUpperCase()}
                          </span>
                        </div>
                      ) : (
                        <div className={`h-24 flex items-center justify-center ${ev?.bg ?? 'bg-secondaryGray-200'}`}>
                          {ev
                            ? <ev.Icon size={32} className={ev.color} />
                            : <AlertCircle size={28} className="text-secondaryGray-500" />
                          }
                        </div>
                      )}

                      {/* Info */}
                      <div className="p-3 space-y-1.5">
                        <div className="flex items-center gap-2">
                          {ev && <ev.Icon size={13} className={ev.color} />}
                          <p className="text-sm font-semibold text-navy-700 leading-tight truncate">
                            {EVENT_LABELS[al.event_type] ?? al.event_type}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs text-secondaryGray-600">
                          <Camera size={11} />
                          <span className="truncate">{al.video_title}</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs text-secondaryGray-500">
                          <Clock size={11} />
                          <span>{dateStr} {timeStr}</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="py-10 text-center text-secondaryGray-500 text-sm flex flex-col items-center gap-2">
                <AlertCircle size={36} className="opacity-30" />
                {filter === 'all' ? 'Aucune alerte enregistrée' : `Aucune alerte de type "${FILTERS.find(f=>f.key===filter)?.label}"`}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
