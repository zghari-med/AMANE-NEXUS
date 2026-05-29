import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, Trash2, Play, AlertTriangle, AlertCircle, Info, ChevronLeft, Activity, Camera, Wifi, WifiOff, X } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import toast from 'react-hot-toast'

import { API, captureUrl } from '../services/api'

const RISK_CONFIG = {
  critical: { color: 'bg-red-100 border-red-400 text-red-800',    dot: 'bg-red-500',    icon: AlertTriangle },
  high:     { color: 'bg-orange-100 border-orange-400 text-orange-800', dot: 'bg-orange-500', icon: AlertCircle },
  medium:   { color: 'bg-yellow-100 border-yellow-400 text-yellow-800', dot: 'bg-yellow-500', icon: AlertCircle },
  low:      { color: 'bg-blue-100 border-blue-400 text-blue-800',  dot: 'bg-blue-400',   icon: Info },
}

const EVENT_LABELS = {
  fall: 'Chute détectée',
  crowding: 'Attroupement',
  abandoned: 'Objet abandonné',
}

/** Format seconds → "m:ss" or "h:mm:ss" */
function fmtDuration(sec) {
  if (!sec || isNaN(sec)) return '—'
  const s = Math.round(sec)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = s % 60
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`
  return `${m}:${String(ss).padStart(2,'0')}`
}

/** Video card thumbnail — loads first frame via metadata */
function VideoThumb({ src }) {
  const ref = useRef(null)
  return (
    <video
      ref={ref}
      src={src}
      preload="metadata"
      muted
      playsInline
      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
      onLoadedMetadata={e => { e.target.currentTime = 1 }}
    />
  )
}

export default function VideosPage() {
  const { token } = useAuthStore()
  const headers   = { Authorization: `Bearer ${token}` }
  const capture   = (f) => captureUrl(f, token)

  /* ── videos ── */
  const [videos,    setVideos]    = useState([])
  const [loading,   setLoading]   = useState(false)
  const [uploading, setUploading] = useState(false)
  const [activeVideo, setActiveVideo] = useState(null)
  const [analysis,  setAnalysis]  = useState(null)
  const [alerts,    setAlerts]    = useState([])
  const [analyzing, setAnalyzing] = useState(false)
  const pollRef  = useRef(null)
  const videoRef = useRef(null)

  /* ── cameras ── */
  const [cameras,     setCameras]     = useState([])
  const [showCamForm, setShowCamForm] = useState(false)
  const [camForm,     setCamForm]     = useState({ name:'', url:'', location:'', type:'http' })
  const [camLoading,  setCamLoading]  = useState(false)
  const [activeCam,   setActiveCam]   = useState(null)

  /* ── live analysis ── */
  const [liveRunning, setLiveRunning] = useState(false)
  const [liveStatus,  setLiveStatus]  = useState('idle')
  const [liveAlerts,  setLiveAlerts]  = useState([])
  const [liveStats,   setLiveStats]   = useState({ total_events:0, falls_detected:0, crowds_detected:0, abandoned_objects:0 })
  const liveLastSince = useRef(null)
  const livePollRef   = useRef(null)

  useEffect(() => { fetchVideos(); fetchCameras() }, [])
  useEffect(() => () => { clearInterval(pollRef.current); clearInterval(livePollRef.current) }, [])

  /* ── fetch ── */
  const fetchVideos = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/videos`, { headers })
      const d = await r.json()
      setVideos(d.videos || [])
    } catch { toast.error('Erreur chargement vidéos') }
    finally { setLoading(false) }
  }

  const fetchCameras = async () => {
    try {
      const r = await fetch(`${API}/api/cameras`, { headers })
      if (!r.ok) return
      const d = await r.json()
      setCameras(d.cameras || [])
    } catch { /* ignore */ }
  }

  /* ── video analysis ── */
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
      if (['completed','failed'].includes(aData.analysis?.status)) {
        clearInterval(pollRef.current)
        setAnalyzing(false)
        if (aData.analysis.status === 'completed') toast.success('Analyse terminée !')
      }
    } catch { /* ignore */ }
  }, [token])

  /** Start analysis for a given video object (called automatically on open) */
  const launchAnalysis = useCallback(async (video) => {
    setAnalyzing(true)
    setAnalysis(null)
    setAlerts([])
    clearInterval(pollRef.current)
    try {
      const r = await fetch(`${API}/api/analyses/create`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: video._id }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      pollRef.current = setInterval(() => fetchAnalysisState(d.analysis_id), 3000)
      fetchAnalysisState(d.analysis_id)
    } catch (e) {
      toast.error('Analyse : ' + e.message)
      setAnalyzing(false)
    }
  }, [token, fetchAnalysisState])

  const openVideo = useCallback((v) => {
    clearInterval(livePollRef.current)
    clearInterval(pollRef.current)
    setActiveCam(null)
    setActiveVideo(v)
    setAnalysis(null); setAlerts([]); setAnalyzing(false)
    // auto-launch
    launchAnalysis(v)
  }, [launchAnalysis])

  const closeVideo = () => {
    clearInterval(pollRef.current)
    setActiveVideo(null)
    setAnalysis(null)
    setAlerts([])
    setAnalyzing(false)
  }

  /** Manual re-run (button in detail view) */
  const handleAnalyze = () => {
    if (activeVideo) launchAnalysis(activeVideo)
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('title', file.name.split('.')[0])
    setUploading(true)
    try {
      const r = await fetch(`${API}/api/videos/upload`, { method:'POST', headers, body: fd })
      if (!r.ok) throw new Error()
      toast.success('Vidéo uploadée !')
      fetchVideos()
    } catch { toast.error("Erreur lors de l'upload") }
    finally { setUploading(false) }
  }

  const handleDelete = async (videoId, e) => {
    e.stopPropagation()
    if (!confirm('Supprimer cette vidéo ?')) return
    try {
      const r = await fetch(`${API}/api/videos/${videoId}`, { method:'DELETE', headers })
      if (!r.ok) throw new Error()
      toast.success('Vidéo supprimée')
      if (activeVideo?._id === videoId) closeVideo()
      fetchVideos()
    } catch { toast.error('Erreur suppression') }
  }

  /* ── camera CRUD ── */
  const handleAddCamera = async (e) => {
    e.preventDefault()
    if (!camForm.name || !camForm.url) { toast.error('Nom et URL requis'); return }
    setCamLoading(true)
    try {
      const r = await fetch(`${API}/api/cameras`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(camForm),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      // Immediately show the new camera card (optimistic)
      if (d.camera) setCameras(prev => [d.camera, ...prev])
      toast.success('Caméra ajoutée !')
      setCamForm({ name:'', url:'', location:'', type:'http' })
      setShowCamForm(false)
      // Refresh from server in background to sync state
      fetchCameras()
    } catch (err) { toast.error(err.message) }
    finally { setCamLoading(false) }
  }

  const handleDeleteCamera = async (camId, e) => {
    e.stopPropagation()
    if (!confirm('Supprimer cette caméra ?')) return
    try {
      await fetch(`${API}/api/cameras/${camId}`, { method:'DELETE', headers })
      toast.success('Caméra supprimée')
      if (activeCam?._id === camId) closeCam()
      fetchCameras()
    } catch { toast.error('Erreur suppression') }
  }

  /* ── live camera analysis ── */
  const pollLiveStatus = useCallback(async (camId) => {
    try {
      const since = liveLastSince.current ? `?since=${liveLastSince.current}` : ''
      const r = await fetch(`${API}/api/cameras/${camId}/live/status${since}`, { headers })
      const d = await r.json()
      setLiveRunning(d.running); setLiveStatus(d.status)
      setLiveStats({
        total_events:      d.total_events      ?? 0,
        falls_detected:    d.falls_detected    ?? 0,
        crowds_detected:   d.crowds_detected   ?? 0,
        abandoned_objects: d.abandoned_objects ?? 0,
      })
      if (d.alerts?.length > 0) {
        setLiveAlerts(prev => {
          const ids = new Set(prev.map(a => a._id))
          return [...d.alerts.filter(a => !ids.has(a._id)), ...prev].slice(0, 100)
        })
        liveLastSince.current = d.alerts[0].created_at
      }
      if (!d.running) clearInterval(livePollRef.current)
    } catch { /* ignore */ }
  }, [token])

  const openCam = (cam) => {
    clearInterval(pollRef.current)
    setActiveVideo(null)
    setActiveCam(cam)
    setLiveRunning(false); setLiveStatus('idle')
    setLiveAlerts([]); liveLastSince.current = null
    setLiveStats({ total_events:0, falls_detected:0, crowds_detected:0, abandoned_objects:0 })
  }

  const closeCam = () => {
    if (liveRunning && activeCam) stopLiveAnalysis(activeCam)
    clearInterval(livePollRef.current)
    setActiveCam(null); setLiveRunning(false); setLiveStatus('idle'); setLiveAlerts([])
  }

  const startLiveAnalysis = async (cam) => {
    setLiveStatus('pending')
    try {
      const r = await fetch(`${API}/api/cameras/${cam._id}/live/start`, { method:'POST', headers })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      setLiveRunning(true)
      toast.success('Analyse démarrée !')
      livePollRef.current = setInterval(() => pollLiveStatus(cam._id), 3000)
    } catch (err) { setLiveStatus('failed'); toast.error(err.message) }
  }

  const stopLiveAnalysis = async (cam) => {
    try {
      await fetch(`${API}/api/cameras/${cam._id}/live/stop`, { method:'POST', headers })
      setLiveRunning(false); clearInterval(livePollRef.current)
      toast.success('Analyse arrêtée')
    } catch { /* ignore */ }
  }

  const progress = analysis?.progress ?? (analyzing ? 30 : 0)
  const statusLabel = {
    pending:'En attente...', processing:'Analyse en cours...',
    completed:'Analyse terminée', failed:'Échec',
  }[analysis?.status] ?? (analyzing ? 'Initialisation...' : '')

  const isDetail = activeVideo || activeCam

  /* ════════════════════════════════════════════════════════ */
  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">

        {/* ── Top bar ── */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            {isDetail && (
              <button onClick={activeVideo ? closeVideo : closeCam}
                className="p-1 hover:bg-gray-100 rounded-lg transition">
                <ChevronLeft size={22} />
              </button>
            )}
            <h1 className="text-2xl font-bold text-gray-900">
              {activeVideo ? activeVideo.title : activeCam ? activeCam.name : 'Vidéos & Caméras'}
            </h1>
          </div>
          {!isDetail && (
            <div className="flex items-center gap-3">
              <button onClick={() => setShowCamForm(true)}
                className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition">
                <Camera size={18} /> Ajouter Caméra IP
              </button>
              <label className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition">
                <Upload size={18} />
                <span>{uploading ? 'Upload…' : 'Upload Vidéo'}</span>
                <input type="file" onChange={handleUpload} className="hidden" accept="video/*" disabled={uploading} />
              </label>
            </div>
          )}
        </div>

        {/* ════════════════════════════════════════════════ */}
        {activeVideo ? (
          /* ── VIDEO analysis view ── */
          <div className="flex-1 flex overflow-hidden">

            {/* LEFT — player + controls */}
            <div className="flex-1 flex flex-col overflow-hidden bg-gray-900">
              <div className="flex-1 relative flex items-center justify-center overflow-hidden">
                <video
                  ref={videoRef}
                  key={activeVideo._id}
                  src={`${API}/api/videos/${activeVideo._id}/file?token=${token}`}
                  className="max-h-full max-w-full rounded"
                  autoPlay controls playsInline
                />
              </div>
              <div className="bg-gray-800 px-5 py-4 shrink-0">
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
                      <div className={`h-2 rounded-full transition-all duration-500 ${
                        analysis?.status === 'completed' ? 'bg-green-500' :
                        analysis?.status === 'failed'    ? 'bg-red-500' : 'bg-blue-500'
                      }`} style={{ width:`${analysis?.status === 'completed' ? 100 : progress}%` }} />
                    </div>
                  </div>
                )}
                {analysis && (
                  <div className="flex gap-6 text-sm text-gray-300 mb-3">
                    <span>🔴 Chutes: <strong className="text-white">{analysis.falls_detected}</strong></span>
                    <span>🟠 Attroupements: <strong className="text-white">{analysis.crowds_detected}</strong></span>
                    <span>🟡 Objets: <strong className="text-white">{analysis.abandoned_objects}</strong></span>
                    <span>📊 Total: <strong className="text-white">{analysis.total_events}</strong></span>
                  </div>
                )}
                <div className="flex gap-3">
                  {analysis?.status === 'completed' && (
                    <button onClick={handleAnalyze}
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition">
                      Relancer l'analyse
                    </button>
                  )}
                  <button onClick={closeVideo}
                    className="px-5 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded-lg transition">
                    Retour aux vidéos
                  </button>
                </div>
              </div>
            </div>

            {/* RIGHT — alerts */}
            <aside className="w-72 shrink-0 bg-white border-l flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b bg-gray-50 flex items-center gap-2">
                <AlertCircle size={18} className="text-red-500" />
                <span className="font-semibold text-gray-800">Alertes</span>
                {alerts.length > 0 && (
                  <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">{alerts.length}</span>
                )}
              </div>
              <div className="flex-1 overflow-y-auto">
                {alerts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm text-center px-4">
                    <AlertCircle size={36} className="mb-3 opacity-30" />
                    <p>{analyzing ? 'En attente des alertes…' : 'Analyse en cours…'}</p>
                  </div>
                ) : (
                  <ul className="divide-y">
                    {alerts.map(al => {
                      const cfg  = RISK_CONFIG[al.risk_level] ?? RISK_CONFIG.low
                      const Icon = cfg.icon
                      return (
                        <li key={al._id} className={`border-l-4 ${cfg.color}`}>
                          {al.capture && (
                            <img src={capture(al.capture)} alt={al.event_type}
                              className="w-full object-cover" style={{ maxHeight:'140px' }}
                              onError={e => { e.target.style.display='none' }} />
                          )}
                          <div className="px-3 py-2 flex items-start gap-2">
                            <Icon size={15} className="mt-0.5 shrink-0" />
                            <div className="min-w-0 flex-1">
                              <p className="font-semibold text-sm">{EVENT_LABELS[al.event_type] ?? al.event_type}</p>
                              <p className="text-xs opacity-70 mt-0.5">Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s</p>
                              <span className="inline-block mt-1 text-xs font-bold uppercase tracking-wide px-1.5 py-0.5 rounded">{al.risk_level}</span>
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

        ) : activeCam ? (
          /* ── CAMERA live view ── */
          <div className="flex-1 flex overflow-hidden">

            {/* LEFT — stream + controls */}
            <div className="flex-1 flex flex-col overflow-hidden bg-gray-900">
              <div className="flex-1 relative flex items-center justify-center overflow-hidden p-4">
                <img src={activeCam.url} alt={activeCam.name}
                  className="max-h-full max-w-full rounded object-contain"
                  onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex' }} />
                <div className="hidden flex-col items-center gap-3 text-gray-400">
                  <WifiOff size={52} className="text-red-400 opacity-60" />
                  <p className="text-sm">Flux inaccessible</p>
                  <p className="text-xs text-gray-600 font-mono">{activeCam.url}</p>
                </div>
              </div>
              <div className="bg-gray-800 px-5 py-4 shrink-0">
                {liveStatus !== 'idle' && (
                  <div className="flex gap-6 text-sm text-gray-300 mb-3">
                    <span>🔴 Chutes: <strong className="text-white">{liveStats.falls_detected}</strong></span>
                    <span>🟠 Attroupements: <strong className="text-white">{liveStats.crowds_detected}</strong></span>
                    <span>🟡 Objets: <strong className="text-white">{liveStats.abandoned_objects}</strong></span>
                    <span>📊 Total: <strong className="text-white">{liveStats.total_events}</strong></span>
                  </div>
                )}
                <div className="flex gap-3">
                  {!liveRunning ? (
                    <button onClick={() => startLiveAnalysis(activeCam)}
                      disabled={liveStatus === 'pending'}
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition">
                      {liveStatus === 'pending' ? 'Démarrage…' : "Lancer l'analyse en direct"}
                    </button>
                  ) : (
                    <button onClick={() => stopLiveAnalysis(activeCam)}
                      className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition">
                      Arrêter l'analyse
                    </button>
                  )}
                  <button onClick={closeCam}
                    className="px-5 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm rounded-lg transition">
                    Retour
                  </button>
                </div>
              </div>
            </div>

            {/* RIGHT — live alerts */}
            <aside className="w-72 shrink-0 bg-white border-l flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b bg-gray-50 flex items-center gap-2">
                <AlertCircle size={18} className="text-red-500" />
                <span className="font-semibold text-gray-800">Alertes en direct</span>
                {liveAlerts.length > 0 && (
                  <span className="ml-auto bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">{liveAlerts.length}</span>
                )}
              </div>
              <div className="flex-1 overflow-y-auto">
                {liveAlerts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm text-center px-4">
                    <AlertCircle size={36} className="mb-3 opacity-30" />
                    <p>{liveRunning ? 'En attente des alertes…' : "Lancez l'analyse pour voir les alertes"}</p>
                  </div>
                ) : (
                  <ul className="divide-y">
                    {liveAlerts.map(al => {
                      const cfg  = RISK_CONFIG[al.risk_level] ?? RISK_CONFIG.low
                      const Icon = cfg.icon
                      return (
                        <li key={al._id} className={`border-l-4 ${cfg.color}`}>
                          {al.capture && (
                            <img src={capture(al.capture)} alt={al.event_type}
                              className="w-full object-cover" style={{ maxHeight:'140px' }}
                              onError={e => { e.target.style.display='none' }} />
                          )}
                          <div className="px-3 py-2 flex items-start gap-2">
                            <Icon size={15} className="mt-0.5 shrink-0" />
                            <div className="min-w-0 flex-1">
                              <p className="font-semibold text-sm">{EVENT_LABELS[al.event_type] ?? al.event_type}</p>
                              <p className="text-xs opacity-70 mt-0.5">Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s</p>
                              <span className="inline-block mt-1 text-xs font-bold uppercase tracking-wide px-1.5 py-0.5 rounded">{al.risk_level}</span>
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

        ) : (
          /* ── GRID view ── */
          <div className="flex-1 overflow-auto p-6 space-y-8">

            {/* ── Caméras IP (toujours visible) ── */}
            <div>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse inline-block" />
                Caméras IP en direct
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">

                {/* Card "+ Ajouter" — toujours première */}
                <div
                  onClick={() => setShowCamForm(true)}
                  className="bg-white rounded-xl border-2 border-dashed border-slate-300 hover:border-blue-400 hover:bg-blue-50/30 h-auto min-h-[220px] flex flex-col items-center justify-center gap-3 cursor-pointer transition group">
                  <div className="w-12 h-12 rounded-full bg-slate-100 group-hover:bg-blue-100 flex items-center justify-center transition">
                    <Camera size={22} className="text-slate-400 group-hover:text-blue-500 transition" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-semibold text-slate-600 group-hover:text-blue-600 transition">Ajouter une caméra IP</p>
                    <p className="text-xs text-slate-400 mt-0.5">HTTP · HLS · RTSP</p>
                  </div>
                </div>

                {/* Caméras existantes */}
                {cameras.map(cam => (
                  <div key={cam._id}
                    className="bg-white rounded-xl shadow hover:shadow-md overflow-hidden transition group cursor-pointer"
                    onClick={() => openCam(cam)}>
                    <div className="bg-gray-900 h-40 flex items-center justify-center relative overflow-hidden">
                      {cam.type === 'http' ? (
                        <>
                          <img src={cam.url} alt={cam.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex' }} />
                          <div className="hidden w-full h-full flex-col items-center justify-center text-gray-500 gap-2">
                            <Camera size={36} className="opacity-30" />
                            <span className="text-xs text-gray-600">Aperçu indisponible</span>
                          </div>
                        </>
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-gray-500">
                          <Camera size={36} className="opacity-40" />
                          <span className="text-xs text-gray-600 font-mono truncate max-w-[140px] px-2">{cam.url}</span>
                        </div>
                      )}
                      <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-black/60 backdrop-blur-sm rounded-full px-2.5 py-1">
                        <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                        <span className="text-[10px] text-green-400 font-bold tracking-wide">EN DIRECT</span>
                      </div>
                      <button onClick={e => handleDeleteCamera(cam._id, e)}
                        className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center bg-black/50 hover:bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-all">
                        <Trash2 size={13} />
                      </button>
                      <div className="absolute inset-0 bg-blue-600/0 group-hover:bg-blue-600/10 transition pointer-events-none" />
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-gray-900 truncate leading-tight">{cam.name}</h3>
                      {cam.location && <p className="text-xs text-gray-500 mt-0.5 truncate">{cam.location}</p>}
                      <button onClick={e => { e.stopPropagation(); openCam(cam) }}
                        className="mt-3 w-full py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition">
                        Ouvrir
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* ── Vidéos enregistrées ── */}
            {loading ? (
              <div className="flex items-center justify-center h-40">
                <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full" />
              </div>
            ) : videos.length > 0 ? (
              <div>
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-400 rounded-full inline-block" />
                  Vidéos enregistrées
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                  {videos.map(v => (
                    <div key={v._id}
                      className="bg-white rounded-xl shadow hover:shadow-md overflow-hidden transition group cursor-pointer"
                      onClick={() => openVideo(v)}>
                      <div className="bg-gray-900 h-40 flex items-center justify-center relative overflow-hidden">
                        <VideoThumb src={`${API}/api/videos/${v._id}/file?token=${token}`} />
                        {v.duration && (
                          <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs font-semibold px-1.5 py-0.5 rounded">
                            {fmtDuration(v.duration)}
                          </div>
                        )}
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition bg-black/30">
                          <div className="w-12 h-12 bg-blue-600/90 rounded-full flex items-center justify-center">
                            <Play size={22} className="text-white ml-0.5" />
                          </div>
                        </div>
                        <button onClick={e => handleDelete(v._id, e)}
                          className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center bg-black/50 hover:bg-red-600 text-white rounded-full opacity-0 group-hover:opacity-100 transition-all">
                          <Trash2 size={13} />
                        </button>
                      </div>
                      <div className="p-4">
                        <h3 className="font-semibold text-gray-900 truncate leading-tight">{v.title}</h3>
                        <p className="text-xs text-gray-500 mt-0.5">{v.duration ? fmtDuration(v.duration) : 'Durée inconnue'}</p>
                        <button onClick={e => { e.stopPropagation(); openVideo(v) }}
                          className="mt-3 w-full py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition">
                          Ouvrir
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-40 text-center text-gray-400">
                <Play size={40} className="mb-3 opacity-30" />
                <p className="text-sm">Aucune vidéo — utilisez "Upload Vidéo" pour commencer</p>
              </div>
            )}

          </div>
        )}

        {/* ── Modal Ajouter Caméra ── */}
        {showCamForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowCamForm(false)}>
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
              <div className="bg-slate-800 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-white">
                  <Camera size={17} /><span className="font-semibold">Ajouter une caméra IP</span>
                </div>
                <button onClick={() => setShowCamForm(false)} className="text-slate-400 hover:text-white transition">
                  <X size={18} />
                </button>
              </div>
              <form onSubmit={handleAddCamera} className="p-6 space-y-4">
                <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <span className="text-xs text-amber-700 flex-1">🎬 Caméra IP Locale — IP Webcam pour tester</span>
                  <button type="button"
                    onClick={() => setCamForm({ name:'Caméra IP Locale — IP Webcam', url:'http://192.168.0.196:8080/video', location:'Réseau local', type:'http' })}
                    className="shrink-0 px-3 py-1.5 bg-amber-500 text-white text-xs font-semibold rounded-lg hover:bg-amber-600 transition flex items-center gap-1.5">
                    <Camera size={12} /> Remplir
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Nom *</label>
                    <input type="text" value={camForm.name} onChange={e => setCamForm(f => ({ ...f, name: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Caméra Rue Principale" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Emplacement</label>
                    <input type="text" value={camForm.location} onChange={e => setCamForm(f => ({ ...f, location: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Bd Mohammed V, Rabat" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">URL du flux *</label>
                    <input type="text" value={camForm.url} onChange={e => setCamForm(f => ({ ...f, url: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="http://ip:port/video" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">Type</label>
                    <select value={camForm.type} onChange={e => setCamForm(f => ({ ...f, type: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      <option value="http">HTTP / MJPEG</option>
                      <option value="hls">HLS (.m3u8)</option>
                      <option value="rtsp">RTSP</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setShowCamForm(false)}
                    className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 text-sm font-medium transition">
                    Annuler
                  </button>
                  <button type="submit" disabled={camLoading}
                    className="flex-1 py-2.5 bg-slate-800 text-white rounded-xl hover:bg-slate-900 transition text-sm font-medium disabled:opacity-50">
                    {camLoading ? 'Ajout…' : 'Ajouter la caméra'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
