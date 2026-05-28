import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, Trash2, Play, AlertTriangle, AlertCircle, Info, ChevronLeft, Activity } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import toast from 'react-hot-toast'

const API = 'http://localhost:5000'

const RISK_CONFIG = {
  critical: { color: 'bg-red-100 border-red-400 text-red-800', dot: 'bg-red-500', icon: AlertTriangle },
  high:     { color: 'bg-orange-100 border-orange-400 text-orange-800', dot: 'bg-orange-500', icon: AlertCircle },
  medium:   { color: 'bg-yellow-100 border-yellow-400 text-yellow-800', dot: 'bg-yellow-500', icon: AlertCircle },
  low:      { color: 'bg-blue-100 border-blue-400 text-blue-800', dot: 'bg-blue-400', icon: Info },
}

const EVENT_LABELS = {
  fall: 'Chute détectée',
  crowding: 'Attroupement',
  abandoned: 'Objet abandonné',
}

export default function VideosPage() {
  const { token } = useAuthStore()
  const [videos, setVideos]           = useState([])
  const [loading, setLoading]         = useState(false)
  const [uploading, setUploading]     = useState(false)
  const [activeVideo, setActiveVideo] = useState(null)   // video doc
  const [analysis, setAnalysis]       = useState(null)   // analysis doc
  const [alerts, setAlerts]           = useState([])
  const [analyzing, setAnalyzing]     = useState(false)
  const pollRef  = useRef(null)
  const videoRef = useRef(null)

  useEffect(() => { fetchVideos() }, [])
  useEffect(() => () => clearInterval(pollRef.current), [])

  /* ── helpers ─────────────────────────────────────────── */
  const headers = { Authorization: `Bearer ${token}` }

  const fetchVideos = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/videos`, { headers })
      const d = await r.json()
      setVideos(d.videos || [])
    } catch { toast.error('Erreur chargement vidéos') }
    finally   { setLoading(false) }
  }

  const fetchAnalysisState = useCallback(async (analysisId) => {
    try {
      const [aRes, alRes] = await Promise.all([
        fetch(`${API}/api/analyses/${analysisId}`, { headers }),
        fetch(`${API}/api/analyses/${analysisId}/alerts`, { headers }),
      ])
      const aData  = await aRes.json()
      const alData = await alRes.json()
      setAnalysis(aData.analysis)
      setAlerts(alData.alerts || [])

      if (['completed', 'failed'].includes(aData.analysis?.status)) {
        clearInterval(pollRef.current)
        setAnalyzing(false)
        if (aData.analysis.status === 'completed') toast.success('Analyse terminée !')
      }
    } catch { /* silently ignore poll errors */ }
  }, [token])

  /* ── actions ─────────────────────────────────────────── */
  const openVideo = (video) => {
    setActiveVideo(video)
    setAnalysis(null)
    setAlerts([])
    setAnalyzing(false)
    clearInterval(pollRef.current)
  }

  const closeVideo = () => {
    clearInterval(pollRef.current)
    setActiveVideo(null)
    setAnalysis(null)
    setAlerts([])
    setAnalyzing(false)
  }

  const handleAnalyze = async () => {
    if (!activeVideo) return
    setAnalyzing(true)
    // auto-play the video
    videoRef.current?.play()
    try {
      const r = await fetch(`${API}/api/analyses/create`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: activeVideo._id }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      toast.success('Analyse lancée !')
      // start polling every 3s
      pollRef.current = setInterval(() => fetchAnalysisState(d.analysis_id), 3000)
      fetchAnalysisState(d.analysis_id)
    } catch (e) {
      toast.error('Erreur : ' + e.message)
      setAnalyzing(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', file.name.split('.')[0])
    setUploading(true)
    try {
      const r = await fetch(`${API}/api/videos/upload`, { method: 'POST', headers, body: fd })
      if (!r.ok) throw new Error()
      toast.success('Vidéo uploadée !')
      fetchVideos()
    } catch { toast.error("Erreur lors de l'upload") }
    finally   { setUploading(false) }
  }

  const handleDelete = async (videoId, e) => {
    e.stopPropagation()
    if (!confirm('Supprimer cette vidéo ?')) return
    try {
      const r = await fetch(`${API}/api/videos/${videoId}`, { method: 'DELETE', headers })
      if (!r.ok) throw new Error()
      toast.success('Vidéo supprimée')
      if (activeVideo?._id === videoId) closeVideo()
      fetchVideos()
    } catch { toast.error('Erreur suppression') }
  }

  const progress = analysis?.progress ?? (analyzing ? 30 : 0)
  const statusLabel = {
    pending:    'En attente...',
    processing: 'Analyse en cours...',
    completed:  'Analyse terminée',
    failed:     'Échec',
  }[analysis?.status] ?? (analyzing ? 'Initialisation...' : '')

  /* ── render ──────────────────────────────────────────── */
  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      <Sidebar />

      {/* ── main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* top bar */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            {activeVideo && (
              <button onClick={closeVideo} className="p-1 hover:bg-gray-100 rounded-lg transition">
                <ChevronLeft size={22} />
              </button>
            )}
            <h1 className="text-2xl font-bold text-gray-900">
              {activeVideo ? activeVideo.title : 'Vidéos'}
            </h1>
          </div>
          {!activeVideo && (
            <label className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition">
              <Upload size={18} />
              <span>{uploading ? 'Upload…' : 'Upload Vidéo'}</span>
              <input type="file" onChange={handleUpload} className="hidden" accept="video/*" disabled={uploading} />
            </label>
          )}
        </div>

        {/* content */}
        {!activeVideo ? (
          /* ── video grid ── */
          <div className="flex-1 overflow-auto p-6">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full" />
              </div>
            ) : videos.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Play size={56} className="text-gray-300 mb-4" />
                <p className="text-gray-500 mb-6">Aucune vidéo uploadée</p>
                <label className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700">
                  <Upload size={18} /> Uploader une vidéo
                  <input type="file" onChange={handleUpload} className="hidden" accept="video/*" />
                </label>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {videos.map(v => (
                  <div
                    key={v._id}
                    onClick={() => openVideo(v)}
                    className="bg-white rounded-xl shadow hover:shadow-md cursor-pointer overflow-hidden transition group"
                  >
                    <div className="bg-gray-900 h-36 flex items-center justify-center relative">
                      <Play size={40} className="text-gray-500 group-hover:text-white transition" />
                      <div className="absolute inset-0 bg-blue-600/0 group-hover:bg-blue-600/10 transition" />
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-gray-900 truncate">{v.title}</h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {v.duration ? `${Math.round(v.duration)}s` : 'Durée inconnue'}
                      </p>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); openVideo(v) }}
                          className="flex-1 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition"
                        >
                          Ouvrir
                        </button>
                        <button
                          onClick={(e) => handleDelete(v._id, e)}
                          className="px-3 py-1.5 bg-red-100 text-red-600 text-sm rounded-lg hover:bg-red-200 transition"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* ── analysis view ── */
          <div className="flex-1 flex overflow-hidden">

            {/* LEFT — video + progress */}
            <div className="flex-1 flex flex-col overflow-hidden bg-gray-900">

              {/* video */}
              <div className="flex-1 relative flex items-center justify-center overflow-hidden">
                <video
                  ref={videoRef}
                  key={activeVideo._id}
                  src={`${API}/api/videos/${activeVideo._id}/file?token=${token}`}
                  className="max-h-full max-w-full rounded"
                  autoPlay
                  controls
                  playsInline
                />
              </div>

              {/* bottom bar */}
              <div className="bg-gray-800 px-5 py-4 shrink-0">
                {/* progress bar */}
                {(analyzing || analysis) && (
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span className="flex items-center gap-1">
                        <Activity size={12} className={analyzing && analysis?.status !== 'completed' ? 'animate-pulse text-blue-400' : 'text-green-400'} />
                        {statusLabel}
                      </span>
                      <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          analysis?.status === 'completed' ? 'bg-green-500' :
                          analysis?.status === 'failed'    ? 'bg-red-500' : 'bg-blue-500'
                        }`}
                        style={{ width: `${analysis?.status === 'completed' ? 100 : progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* stats row */}
                {analysis && (
                  <div className="flex gap-6 text-sm text-gray-300 mb-3">
                    <span>🔴 Chutes: <strong className="text-white">{analysis.falls_detected}</strong></span>
                    <span>🟠 Attroupements: <strong className="text-white">{analysis.crowds_detected}</strong></span>
                    <span>🟡 Objets: <strong className="text-white">{analysis.abandoned_objects}</strong></span>
                    <span>📊 Total: <strong className="text-white">{analysis.total_events}</strong></span>
                  </div>
                )}

                {/* action buttons */}
                <div className="flex gap-3">
                  {!analyzing && !analysis && (
                    <button
                      onClick={handleAnalyze}
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition"
                    >
                      Lancer l'analyse
                    </button>
                  )}
                  {analysis?.status === 'completed' && (
                    <button
                      onClick={handleAnalyze}
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition"
                    >
                      Relancer l'analyse
                    </button>
                  )}
                  <button
                    onClick={closeVideo}
                    className="px-5 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded-lg transition"
                  >
                    Retour aux vidéos
                  </button>
                </div>
              </div>

            </div>

            {/* RIGHT — alerts panel */}
            <aside className="w-72 shrink-0 bg-white border-l flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b bg-gray-50 flex items-center gap-2">
                <AlertCircle size={18} className="text-red-500" />
                <span className="font-semibold text-gray-800">Alertes</span>
                {alerts.length > 0 && (
                  <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    {alerts.length}
                  </span>
                )}
              </div>

              <div className="flex-1 overflow-y-auto">
                {alerts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm text-center px-4">
                    <AlertCircle size={36} className="mb-3 opacity-30" />
                    <p>{analyzing ? 'En attente des alertes…' : 'Lancez une analyse pour voir les alertes'}</p>
                  </div>
                ) : (
                  <ul className="divide-y">
                    {alerts.map(al => {
                      const cfg = RISK_CONFIG[al.risk_level] ?? RISK_CONFIG.low
                      const Icon = cfg.icon
                      return (
                        <li key={al._id} className={`border-l-4 ${cfg.color} transition`}>
                          {/* Capture image */}
                          {al.capture && (
                            <img
                              src={`${API}/api/captures/${al.capture}`}
                              alt={al.event_type}
                              className="w-full object-cover"
                              style={{ maxHeight: '140px' }}
                              onError={e => { e.target.style.display = 'none' }}
                            />
                          )}
                          <div className="px-3 py-2 flex items-start gap-2">
                            <Icon size={15} className="mt-0.5 shrink-0" />
                            <div className="min-w-0 flex-1">
                              <p className="font-semibold text-sm">
                                {EVENT_LABELS[al.event_type] ?? al.event_type}
                              </p>
                              <p className="text-xs opacity-70 mt-0.5">
                                Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s
                              </p>
                              <span className="inline-block mt-1 text-xs font-bold uppercase tracking-wide px-1.5 py-0.5 rounded">
                                {al.risk_level}
                              </span>
                            </div>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            </aside>

          </div>
        )}
      </div>
    </div>
  )
}
