import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, Trash2, Play, AlertTriangle, AlertCircle, Info, ChevronLeft, Activity, Camera, Wifi, WifiOff, X, PersonStanding, Users, Package, BarChart3 } from 'lucide-react'
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

  /* ── Alert panel (shared) ── */
  const AlertPanel = ({ items, isLive }) => (
    <aside className="w-72 shrink-0 bg-white border-l border-secondaryGray-200 flex flex-col overflow-hidden">
      <div className="px-4 py-3.5 border-b border-secondaryGray-200 flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl bg-red-50 flex items-center justify-center">
          <AlertCircle size={16} className="text-red-500" />
        </div>
        <span className="font-semibold text-navy-700 text-sm">{isLive ? 'Alertes en direct' : 'Alertes'}</span>
        {items.length > 0 && (
          <span className="ml-auto bg-red-500 text-white text-xs font-bold w-5 h-5 flex items-center justify-center rounded-full">{items.length}</span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-secondaryGray-500 text-sm text-center px-4 py-8">
            <AlertCircle size={32} className="mb-3 opacity-20" />
            <p>{isLive
              ? (liveRunning ? 'En attente des alertes…' : "Lancez l'analyse pour voir les alertes")
              : (analyzing ? 'Analyse en cours…' : 'Aucune alerte')
            }</p>
          </div>
        ) : (
          items.map(al => {
            const cfg  = RISK_CONFIG[al.risk_level] ?? RISK_CONFIG.low
            const Icon = cfg.icon
            const evIcon = { fall: PersonStanding, crowding: Users, abandoned: Package }[al.event_type] ?? AlertCircle
            const EvIcon = evIcon
            return (
              <div key={al._id} className="bg-secondaryGray-300 rounded-xl overflow-hidden">
                {al.capture && (
                  <img src={capture(al.capture)} alt={al.event_type}
                    className="w-full object-cover rounded-t-xl" style={{ maxHeight:'120px' }}
                    onError={e => { e.target.style.display='none' }} />
                )}
                <div className="px-3 py-2.5 flex items-start gap-2">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    al.event_type === 'fall' ? 'bg-red-100' :
                    al.event_type === 'crowding' ? 'bg-orange-100' : 'bg-blue-100'
                  }`}>
                    <EvIcon size={14} className={
                      al.event_type === 'fall' ? 'text-red-500' :
                      al.event_type === 'crowding' ? 'text-orange-500' : 'text-blue-500'
                    } />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-navy-700 text-xs leading-tight">{EVENT_LABELS[al.event_type] ?? al.event_type}</p>
                    <p className="text-[11px] text-secondaryGray-600 mt-0.5">Frame {al.frame_id} · {Number(al.timestamp).toFixed(1)}s</p>
                    <span className={`inline-block mt-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${cfg.color}`}>{al.risk_level}</span>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </aside>
  )

  /* ════════════════════════════════════════════════════════ */
  return (
    <div className="flex h-screen bg-secondaryGray-300 overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">

        {/* ── Top bar ── */}
        <div className="bg-white border-b border-secondaryGray-200 px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            {isDetail && (
              <button onClick={activeVideo ? closeVideo : closeCam}
                className="w-9 h-9 flex items-center justify-center hover:bg-secondaryGray-300 rounded-xl transition">
                <ChevronLeft size={20} className="text-navy-700" />
              </button>
            )}
            <h1 className="text-2xl font-bold text-navy-700">
              {activeVideo ? activeVideo.title : activeCam ? activeCam.name : 'Vidéos & Caméras'}
            </h1>
          </div>
          {!isDetail && (
            <div className="flex items-center gap-3">
              <button onClick={() => setShowCamForm(true)}
                className="flex items-center gap-2 px-4 py-2 bg-navy-700 text-white rounded-xl text-sm font-medium hover:bg-navy-800 transition">
                <Camera size={16} /> Ajouter Caméra IP
              </button>
              <label className="flex items-center gap-2 px-4 py-2 rounded-xl cursor-pointer text-sm font-medium text-white transition"
                style={{ background: 'linear-gradient(135deg, #868CFF 0%, #4318FF 100%)' }}>
                <Upload size={16} />
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
            <div className="flex-1 flex flex-col overflow-y-auto bg-secondaryGray-300 p-5 gap-4">

              {/* Video player card */}
              <div className="bg-white rounded-2xl shadow-horizon overflow-hidden">
                <video
                  ref={videoRef}
                  key={activeVideo._id}
                  src={`${API}/api/videos/${activeVideo._id}/file?token=${token}`}
                  className="w-full max-h-[55vh] object-contain bg-gray-50"
                  autoPlay controls playsInline
                />
              </div>

              {/* Progress + stats card */}
              {(analyzing || analysis) && (
                <div className="bg-white rounded-2xl shadow-horizon p-5">
                  {/* Progress bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-secondaryGray-600 mb-2">
                      <span className="flex items-center gap-1.5">
                        <Activity size={12} className={analyzing && analysis?.status !== 'completed' ? 'animate-pulse text-brand-600' : 'text-green-500'} />
                        <span className="font-medium">{statusLabel}</span>
                      </span>
                      <span className="font-semibold text-navy-700">{progress}%</span>
                    </div>
                    <div className="w-full bg-secondaryGray-300 rounded-full h-2">
                      <div className={`h-2 rounded-full transition-all duration-500 ${
                        analysis?.status === 'completed' ? 'bg-green-500' :
                        analysis?.status === 'failed'    ? 'bg-red-500' : 'bg-brand-600'
                      }`} style={{ width:`${analysis?.status === 'completed' ? 100 : progress}%` }} />
                    </div>
                  </div>

                  {/* Stats chips */}
                  {analysis && (
                    <div className="flex flex-wrap gap-3 mb-4">
                      {[
                        { Icon: PersonStanding, label: 'Chutes',        value: analysis.falls_detected,    bg: 'bg-red-50',    text: 'text-red-600',    num: 'text-red-700'    },
                        { Icon: Users,          label: 'Attroupements', value: analysis.crowds_detected,   bg: 'bg-orange-50', text: 'text-orange-500', num: 'text-orange-700' },
                        { Icon: Package,        label: 'Objets',        value: analysis.abandoned_objects, bg: 'bg-blue-50',   text: 'text-blue-500',   num: 'text-blue-700'   },
                        { Icon: BarChart3,      label: 'Total',         value: analysis.total_events,      bg: 'bg-brand-50',  text: 'text-brand-500',  num: 'text-brand-700'  },
                      ].map(({ Icon, label, value, bg, text, num }) => (
                        <div key={label} className={`flex items-center gap-2 px-3 py-2 rounded-xl ${bg}`}>
                          <Icon size={15} className={text} />
                          <span className="text-xs text-secondaryGray-600">{label} :</span>
                          <span className={`text-sm font-bold ${num}`}>{value ?? 0}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Buttons */}
                  <div className="flex gap-3">
                    {analysis?.status === 'completed' && (
                      <button onClick={handleAnalyze} className="btn-primary text-sm">
                        Relancer l'analyse
                      </button>
                    )}
                    <button onClick={closeVideo} className="btn-secondary text-sm">
                      Retour aux vidéos
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* RIGHT — alerts */}
            <AlertPanel items={alerts} isLive={false} />
          </div>

        ) : activeCam ? (
          /* ── CAMERA live view ── */
          <div className="flex-1 flex overflow-hidden">

            {/* LEFT — stream + controls */}
            <div className="flex-1 flex flex-col overflow-y-auto bg-secondaryGray-300 p-5 gap-4">

              {/* Camera stream card */}
              <div className="bg-white rounded-2xl shadow-horizon overflow-hidden">
                <div className="relative bg-gray-100 flex items-center justify-center min-h-[55vh]">
                  <img src={activeCam.url} alt={activeCam.name}
                    className="w-full max-h-[55vh] object-contain rounded-2xl"
                    onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex' }} />
                  <div className="hidden w-full h-64 flex-col items-center justify-center gap-3 text-secondaryGray-500">
                    <WifiOff size={48} className="text-red-400 opacity-50" />
                    <p className="text-sm font-medium text-navy-700">Flux inaccessible</p>
                    <p className="text-xs text-secondaryGray-600 font-mono">{activeCam.url}</p>
                  </div>
                  {liveRunning && (
                    <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-white/90 backdrop-blur-sm rounded-full px-3 py-1.5 shadow-sm">
                      <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                      <span className="text-xs font-bold text-red-600 tracking-wide">EN DIRECT</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Stats + controls card */}
              <div className="bg-white rounded-2xl shadow-horizon p-5">
                {liveStatus !== 'idle' && (
                  <div className="flex flex-wrap gap-3 mb-4">
                    {[
                      { Icon: PersonStanding, label: 'Chutes',        value: liveStats.falls_detected,    bg: 'bg-red-50',    text: 'text-red-500',    num: 'text-red-700'    },
                      { Icon: Users,          label: 'Attroupements', value: liveStats.crowds_detected,   bg: 'bg-orange-50', text: 'text-orange-500', num: 'text-orange-700' },
                      { Icon: Package,        label: 'Objets',        value: liveStats.abandoned_objects, bg: 'bg-blue-50',   text: 'text-blue-500',   num: 'text-blue-700'   },
                      { Icon: BarChart3,      label: 'Total',         value: liveStats.total_events,      bg: 'bg-brand-50',  text: 'text-brand-500',  num: 'text-brand-700'  },
                    ].map(({ Icon, label, value, bg, text, num }) => (
                      <div key={label} className={`flex items-center gap-2 px-3 py-2 rounded-xl ${bg}`}>
                        <Icon size={15} className={text} />
                        <span className="text-xs text-secondaryGray-600">{label} :</span>
                        <span className={`text-sm font-bold ${num}`}>{value}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-3">
                  {!liveRunning ? (
                    <button onClick={() => startLiveAnalysis(activeCam)}
                      disabled={liveStatus === 'pending'}
                      className="btn-primary text-sm disabled:opacity-50">
                      {liveStatus === 'pending' ? 'Démarrage…' : "Lancer l'analyse en direct"}
                    </button>
                  ) : (
                    <button onClick={() => stopLiveAnalysis(activeCam)}
                      className="px-6 py-2.5 rounded-xl bg-red-500 text-white text-sm font-medium hover:bg-red-600 transition">
                      Arrêter l'analyse
                    </button>
                  )}
                  <button onClick={closeCam} className="btn-secondary text-sm">Retour</button>
                </div>
              </div>
            </div>

            {/* RIGHT — live alerts */}
            <AlertPanel items={liveAlerts} isLive={true} />
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
