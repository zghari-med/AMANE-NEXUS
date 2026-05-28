import { useState, useEffect } from 'react'
import Sidebar from '../components/Sidebar'
import StatCard from '../components/StatCard'
import { Video, Play, BarChart3, AlertCircle, Upload, Trash2 } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import toast from 'react-hot-toast'

const API = 'http://localhost:5000'

const STATUS_LABELS = {
  completed:  'Terminée',
  processing: 'En cours',
  pending:    'En attente',
  failed:     'Échec',
}

export default function DashboardUserPage() {
  const { user, token } = useAuthStore()
  const [videos, setVideos]     = useState([])
  const [analyses, setAnalyses] = useState([])
  const [stats, setStats]       = useState(null)
  const [loading, setLoading]   = useState(true)
  const [uploading, setUploading] = useState(false)

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [vRes, aRes, sRes] = await Promise.all([
        fetch(`${API}/api/videos`,               { headers }),
        fetch(`${API}/api/analyses`,             { headers }),
        fetch(`${API}/api/analyses/statistics`,  { headers }),
      ])
      const [vd, ad, sd] = await Promise.all([vRes.json(), aRes.json(), sRes.json()])
      setVideos(vd.videos || [])
      setAnalyses(ad.analyses || [])
      setStats(sd)
    } catch { toast.error('Erreur lors du chargement') }
    finally { setLoading(false) }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('title', file.name.split('.')[0])
      const r = await fetch(`${API}/api/videos/upload`, { method: 'POST', headers, body: fd })
      if (!r.ok) throw new Error()
      toast.success('Vidéo uploadée !')
      fetchData()
    } catch { toast.error("Erreur lors de l'upload") }
    finally { setUploading(false) }
  }

  const handleDelete = async (videoId) => {
    if (!confirm('Supprimer cette vidéo ?')) return
    try {
      const r = await fetch(`${API}/api/videos/${videoId}`, { method: 'DELETE', headers })
      if (!r.ok) throw new Error()
      toast.success('Vidéo supprimée')
      fetchData()
    } catch { toast.error('Erreur suppression') }
  }

  const handleAnalyze = async (videoId) => {
    try {
      const r = await fetch(`${API}/api/analyses/create`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: videoId }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      toast.success('Analyse lancée ! Rendez-vous dans Vidéos.')
      fetchData()
    } catch (e) { toast.error(e.message) }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-500 text-sm">Bienvenue, {user?.full_name || user?.username}</p>
            </div>
            <label className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition text-sm font-medium">
              <Upload size={16} />
              {uploading ? 'Upload…' : 'Upload Vidéo'}
              <input type="file" onChange={handleUpload} disabled={uploading} accept="video/*" className="hidden" />
            </label>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8">

          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
            <StatCard title="Vidéos"          value={loading ? '…' : (stats?.total_videos ?? 0)}       icon={Video}       color="blue"   />
            <StatCard title="Analyses"        value={loading ? '…' : (stats?.completed_analyses ?? 0)} icon={BarChart3}   color="green"  />
            <StatCard title="Alertes"         value={loading ? '…' : (stats?.total_alerts ?? 0)}       icon={AlertCircle} color="red"    />
            <StatCard title="Total événements" value={loading ? '…' : (stats?.total_events ?? 0)}      icon={Play}        color="purple" />
          </div>

          {/* Videos */}
          <div className="mb-8">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Mes Vidéos</h2>
            {loading ? (
              <div className="bg-white rounded-xl p-10 text-center">
                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
              </div>
            ) : videos.length === 0 ? (
              <div className="bg-white rounded-xl p-12 text-center border">
                <Video size={44} className="mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500 text-sm">Aucune vidéo — uploadez-en une pour commencer</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {videos.map(v => (
                  <div key={v._id} className="bg-white rounded-xl shadow-sm border overflow-hidden hover:shadow-md transition">
                    <div className="bg-gray-900 h-28 flex items-center justify-center">
                      <Play size={32} className="text-gray-500" />
                    </div>
                    <div className="p-4">
                      <p className="font-semibold text-sm text-gray-900 truncate">{v.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {v.duration ? `${Math.round(v.duration)}s` : 'Durée inconnue'}
                      </p>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleAnalyze(v._id)}
                          className="flex-1 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-1"
                        >
                          <Play size={13} /> Analyser
                        </button>
                        <button
                          onClick={() => handleDelete(v._id)}
                          className="px-2.5 py-1.5 bg-red-50 text-red-600 text-xs rounded-lg hover:bg-red-100 transition"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent analyses */}
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-4">Mes Analyses</h2>
            {analyses.length === 0 ? (
              <div className="bg-white rounded-xl p-10 text-center border">
                <BarChart3 size={44} className="mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500 text-sm">Aucune analyse — lancez une analyse depuis Vidéos</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Vidéo</th>
                      <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Statut</th>
                      <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Chutes</th>
                      <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Attroup.</th>
                      <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Obj.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {analyses.slice(0, 8).map(a => (
                      <tr key={a._id} className="hover:bg-gray-50">
                        <td className="px-5 py-3 text-gray-900">{a.video_title || '—'}</td>
                        <td className="px-5 py-3">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                            a.status === 'completed'  ? 'bg-green-100 text-green-700' :
                            a.status === 'processing' ? 'bg-blue-100 text-blue-700' :
                            a.status === 'failed'     ? 'bg-red-100 text-red-700' :
                                                        'bg-gray-100 text-gray-700'
                          }`}>
                            {STATUS_LABELS[a.status] ?? a.status}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-gray-700">{a.falls_detected ?? 0}</td>
                        <td className="px-5 py-3 text-gray-700">{a.crowds_detected ?? 0}</td>
                        <td className="px-5 py-3 text-gray-700">{a.abandoned_objects ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
