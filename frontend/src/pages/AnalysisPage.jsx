import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useAuthStore } from '../context/authStore'
import { AlertCircle, Download, BarChart3, Play, PersonStanding, Users, Package, TrendingDown } from 'lucide-react'
import toast from 'react-hot-toast'
import { motion } from 'framer-motion'

const EVENT_META = {
  fall:      { Icon: PersonStanding, bg: 'bg-red-100',    color: 'text-red-500',    label: 'Chute',            badgeClass: 'bg-red-100 text-red-700'    },
  crowding:  { Icon: Users,          bg: 'bg-orange-100', color: 'text-orange-500', label: 'Attroupement',     badgeClass: 'bg-orange-100 text-orange-700' },
  abandoned: { Icon: Package,        bg: 'bg-blue-100',   color: 'text-blue-500',   label: 'Objet abandonné',  badgeClass: 'bg-blue-100 text-blue-700'   },
}

export default function AnalysisPage() {
  const { analysisId } = useParams()
  const { token } = useAuthStore()
  const [analysis, setAnalysis] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    fetchAnalysis()
  }, [analysisId])

  const fetchAnalysis = async () => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` }

      const analysisRes = await fetch(`/api/analyses/${analysisId}`, { headers })
      const analysisData = await analysisRes.json()
      setAnalysis(analysisData.analysis)

      const alertsRes = await fetch(`/api/analyses/${analysisId}/alerts`, { headers })
      const alertsData = await alertsRes.json()
      setAlerts(alertsData.alerts || [])

      setLoading(false)
    } catch (error) {
      toast.error('Erreur lors du chargement')
      setLoading(false)
    }
  }

  const handleExport = async (format) => {
    try {
      setExporting(true)
      const headers = { 'Authorization': `Bearer ${token}` }
      const response = await fetch(`/api/analyses/${analysisId}/export/${format}`, { headers })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `analysis_${analysisId}.${format}`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        toast.success(`Export ${format.toUpperCase()} réussi!`)
      }
    } catch (error) {
      toast.error('Erreur lors de l\'export')
    } finally {
      setExporting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">Analyse non trouvée</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <h1 className="text-3xl font-bold text-gray-900">{analysis.video_title}</h1>
            <p className="text-gray-600">Analyse de vidéo - Statut: <span className="badge badge-success">{analysis.status}</span></p>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Video Player Area */}
          <div className="card overflow-hidden mb-8">
            <div className="aspect-video bg-gray-900 flex items-center justify-center relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <Play className="mx-auto text-gray-600 mb-4" size={64} />
                  <p className="text-gray-400">Lecteur vidéo avec overlay en direct</p>
                </div>
              </div>
            </div>
          </div>

          {/* Stats & Export */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Analysis Stats */}
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Résumé de l'Analyse</h3>
              <div className="space-y-3">
                {/* Total */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-gray-200 flex items-center justify-center">
                      <BarChart3 size={18} className="text-gray-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">Total événements</span>
                  </div>
                  <span className="text-xl font-bold text-gray-900">{analysis.total_events ?? 0}</span>
                </div>
                {/* Chutes */}
                <div className="flex items-center justify-between p-3 bg-red-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-red-100 flex items-center justify-center">
                      <PersonStanding size={18} className="text-red-500" />
                    </div>
                    <span className="text-sm font-medium text-red-700">Chutes détectées</span>
                  </div>
                  <span className="text-xl font-bold text-red-600">{analysis.falls_detected ?? 0}</span>
                </div>
                {/* Attroupements */}
                <div className="flex items-center justify-between p-3 bg-orange-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-orange-100 flex items-center justify-center">
                      <Users size={18} className="text-orange-500" />
                    </div>
                    <span className="text-sm font-medium text-orange-700">Attroupements</span>
                  </div>
                  <span className="text-xl font-bold text-orange-600">{analysis.crowds_detected ?? 0}</span>
                </div>
                {/* Objets abandonnés */}
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center">
                      <Package size={18} className="text-blue-500" />
                    </div>
                    <span className="text-sm font-medium text-blue-700">Objets abandonnés</span>
                  </div>
                  <span className="text-xl font-bold text-blue-600">{analysis.abandoned_objects ?? 0}</span>
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Performance</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">FPS Moyen</span>
                    <span className="font-semibold">{analysis.average_fps?.toFixed(1) || 'N/A'}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: '75%' }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">CPU Usage</span>
                    <span className="font-semibold">{analysis.cpu_usage?.toFixed(1) || 'N/A'}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '45%' }}></div>
                  </div>
                </div>
                <div className="text-sm text-gray-600">
                  <p>Traitement: {analysis.processing_time?.toFixed(2) || 'N/A'}s</p>
                </div>
              </div>
            </div>

            {/* Export Options */}
            <div className="card p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Exporter Données</h3>
              <div className="space-y-2">
                {['csv', 'json', 'pdf'].map((format) => (
                  <button
                    key={format}
                    onClick={() => handleExport(format)}
                    disabled={exporting}
                    className="w-full btn-secondary flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <Download size={18} />
                    {format.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Alerts List */}
          <div className="card">
            <div className="p-6 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <AlertCircle size={20} />
                Alertes Détectées ({alerts.length})
              </h3>
            </div>

            {alerts.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-gray-500">Aucune alerte générée</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                {alerts.map((alert, idx) => (
                  <motion.div
                    key={alert.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {/* Icône comportement */}
                      {(() => {
                        const meta = EVENT_META[alert.event_type]
                        if (!meta) return <AlertCircle size={20} className="text-gray-400 flex-shrink-0" />
                        return (
                          <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${meta.bg}`}>
                            <meta.Icon size={18} className={meta.color} />
                          </div>
                        )
                      })()}
                      {/* Infos */}
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-gray-900 text-sm">
                          {EVENT_META[alert.event_type]?.label ?? alert.event_type}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Frame {alert.frame_id} · {Number(alert.timestamp).toFixed(1)}s
                        </p>
                      </div>
                      {/* Badge risque */}
                      <span className={`badge flex-shrink-0 ${
                        EVENT_META[alert.event_type]?.badgeClass ?? 'bg-gray-100 text-gray-700'
                      }`}>
                        {alert.risk_level}
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
