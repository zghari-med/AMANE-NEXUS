import { useState, useEffect, useRef } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LabelList, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import StatCard from '../components/StatCard'
import {
  BarChart3, AlertCircle, Video, TrendingUp,
  Download, FileText, Sheet, FileSpreadsheet,
  Camera, Clock, ChevronLeft, ChevronRight, Search,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { API, captureUrl } from '../services/api'

const TYPE_COLORS = { fall: '#ef4444', crowding: '#f59e0b', abandoned: '#3b82f6' }
const PIE_COLORS  = ['#ef4444', '#f59e0b', '#3b82f6']

const EVENT_LABELS = { fall: 'Chute', crowding: 'Attroupement', abandoned: 'Objet abandonné' }

/* ── Custom bar label ──────────────────────────────────────────────── */
const BarLabel = ({ x, y, width, value }) =>
  value > 0 ? (
    <text x={x + width / 2} y={y - 4} textAnchor="middle" fontSize={10} fill="#6b7280">
      {value}
    </text>
  ) : null

/* ── Export helpers ────────────────────────────────────────────────── */
const buildRows = (alerts) => alerts.map(al => ({
  Type:        EVENT_LABELS[al.event_type] || al.event_type,
  Caméra:      al.video_title,
  Date:        al.created_at ? new Date(al.created_at).toLocaleDateString('fr-FR') : '—',
  Heure:       al.created_at ? new Date(al.created_at).toLocaleTimeString('fr-FR') : '—',
  Frame:       al.frame_id,
  Timestamp_s: al.timestamp,
  Risque:      al.risk_level,
}))

async function exportCSV(alerts) {
  const rows = buildRows(alerts)
  const header = Object.keys(rows[0]).join(';')
  const body   = rows.map(r => Object.values(r).join(';')).join('\n')
  const blob = new Blob(['﻿' + header + '\n' + body], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a'); a.href = url; a.download = 'alertes.csv'; a.click()
  URL.revokeObjectURL(url)
}

async function exportExcel(alerts) {
  const { utils, writeFile } = await import('xlsx')
  const ws = utils.json_to_sheet(buildRows(alerts))
  const wb = utils.book_new()
  utils.book_append_sheet(wb, ws, 'Alertes')
  writeFile(wb, 'alertes.xlsx')
}

async function exportPDF(alerts) {
  const { default: jsPDF } = await import('jspdf')
  const { default: autoTable } = await import('jspdf-autotable')
  const doc = new jsPDF({ orientation: 'landscape' })
  doc.setFontSize(14)
  doc.text('AMANE-NEXUS — Journal des Alertes', 14, 15)
  doc.setFontSize(9)
  doc.text(`Exporté le ${new Date().toLocaleString('fr-FR')}`, 14, 22)
  autoTable(doc, {
    startY: 28,
    head: [['Type', 'Caméra', 'Date', 'Heure', 'Frame', 'Temps (s)', 'Risque']],
    body: buildRows(alerts).map(r => Object.values(r)),
    styles: { fontSize: 8, cellPadding: 3 },
    headStyles: { fillColor: [30, 58, 95], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [245, 247, 250] },
    columnStyles: {
      0: { cellWidth: 35 }, 1: { cellWidth: 45 }, 6: { cellWidth: 22 }
    },
  })
  doc.save('alertes.pdf')
}

/* ══════════════════════════════════════════════════════════════════════════ */
export default function StatisticsPage() {
  const { token } = useAuthStore()
  const [stats,   setStats]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [days,    setDays]    = useState(7)

  // Export / alerts table state
  const [allAlerts,    setAllAlerts]   = useState([])
  const [loadingExport, setLoadingExport] = useState(false)
  const [exportFmt,    setExportFmt]   = useState('csv')
  const [search,       setSearch]      = useState('')
  const [page,         setPage]        = useState(1)
  const PAGE_SIZE = 10

  const headers = { Authorization: `Bearer ${token}` }
  const capture = (f) => captureUrl(f, token)

  useEffect(() => { fetchStats() }, [days])
  useEffect(() => { fetchAllAlerts() }, [])

  const fetchStats = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/analyses/statistics?days=${days}`, { headers })
      setStats(await r.json())
    } catch { toast.error('Erreur chargement statistiques') }
    finally { setLoading(false) }
  }

  const fetchAllAlerts = async () => {
    try {
      const r = await fetch(`${API}/api/alerts/export`, { headers })
      if (!r.ok) return
      const d = await r.json()
      setAllAlerts(d.alerts || [])
    } catch { /* silently */ }
  }

  const handleExport = async () => {
    if (allAlerts.length === 0) { toast.error('Aucune alerte à exporter'); return }
    setLoadingExport(true)
    try {
      const data = search
        ? allAlerts.filter(a =>
            Object.values(a).some(v => String(v).toLowerCase().includes(search.toLowerCase()))
          )
        : allAlerts
      if (exportFmt === 'csv')   await exportCSV(data)
      if (exportFmt === 'excel') await exportExcel(data)
      if (exportFmt === 'pdf')   await exportPDF(data)
      toast.success(`Export ${exportFmt.toUpperCase()} téléchargé !`)
    } catch (e) { toast.error('Erreur export: ' + e.message) }
    finally { setLoadingExport(false) }
  }

  // Pie data
  const pieData = stats ? [
    { name: 'Chutes',            value: stats.alerts_by_type?.fall      || 0 },
    { name: 'Attroupements',     value: stats.alerts_by_type?.crowding  || 0 },
    { name: 'Objets abandonnés', value: stats.alerts_by_type?.abandoned || 0 },
  ].filter(d => d.value > 0) : []

  // Composed chart — add total line
  const chartData = (stats?.chart_data || []).map(d => ({
    ...d,
    total: (d.chutes || 0) + (d.attroupements || 0) + (d.objets || 0),
  }))

  // Filtered + paginated alerts
  const filtered = allAlerts.filter(a =>
    !search || Object.values(a).some(v => String(v).toLowerCase().includes(search.toLowerCase()))
  )
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageData   = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Statistiques</h1>
            </div>
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

        <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">

          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full" />
            </div>
          ) : (
            <>
              {/* KPI cards — same StatCard component as Dashboard */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
                <StatCard title="Total alertes"    value={stats?.total_alerts   ?? 0} icon={AlertCircle} color="red"    />
                <StatCard title="Analyses"         value={stats?.total_analyses ?? 0} icon={BarChart3}   color="blue"   />
                <StatCard title="Vidéos"           value={stats?.total_videos   ?? 0} icon={Video}       color="purple" />
                <StatCard title="Total événements" value={stats?.total_events   ?? 0} icon={TrendingUp}  color="green"  />
              </div>

              {/* Charts row */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* ── ComposedChart — Bar + Line + valeurs ── */}
                <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border p-6">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="text-base font-semibold text-gray-900">Tendance des Détections</h3>
                    <span className="text-xs text-gray-400">Barres = détections · Ligne = total</span>
                  </div>
                  <p className="text-xs text-gray-400 mb-4">Détections par date d'analyse (JJ/MM/AAAA)</p>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={265}>
                      <ComposedChart data={chartData} margin={{ top: 18, right: 20, left: -10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 10 }} tickLine={false} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{ borderRadius: '10px', fontSize: '12px', border: '1px solid #e5e7eb' }}
                          formatter={(v, name) => [v, name]}
                        />
                        <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: 11 }} />

                        <Bar dataKey="chutes" name="Chutes" fill={TYPE_COLORS.fall}
                             radius={[4,4,0,0]} maxBarSize={28}>
                          <LabelList content={<BarLabel />} />
                        </Bar>
                        <Bar dataKey="attroupements" name="Attroupements" fill={TYPE_COLORS.crowding}
                             radius={[4,4,0,0]} maxBarSize={28}>
                          <LabelList content={<BarLabel />} />
                        </Bar>
                        <Bar dataKey="objets" name="Obj. abandonnés" fill={TYPE_COLORS.abandoned}
                             radius={[4,4,0,0]} maxBarSize={28}>
                          <LabelList content={<BarLabel />} />
                        </Bar>

                        <Line
                          type="monotone" dataKey="total" name="Total"
                          stroke="#6366f1" strokeWidth={2.5}
                          dot={{ r: 4, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }}
                          activeDot={{ r: 6 }}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-60 text-gray-400 text-sm">
                      Aucune analyse complétée
                    </div>
                  )}
                </div>

                {/* Pie chart */}
                <div className="bg-white rounded-xl shadow-sm border p-6">
                  <h3 className="text-base font-semibold text-gray-900 mb-4">Répartition par type</h3>
                  {pieData.length > 0 ? (
                    <>
                      <ResponsiveContainer width="100%" height={190}>
                        <PieChart>
                          <Pie data={pieData} cx="50%" cy="50%"
                               innerRadius={50} outerRadius={80}
                               paddingAngle={4} dataKey="value">
                            {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % 3]} />)}
                          </Pie>
                          <Tooltip formatter={(v, n) => [v, n]} />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="space-y-2.5 mt-1">
                        {pieData.map((d, i) => (
                          <div key={d.name} className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rounded-full" style={{ background: PIE_COLORS[i] }} />
                              <span className="text-gray-600">{d.name}</span>
                            </div>
                            <span className="font-bold" style={{ color: PIE_COLORS[i] }}>{d.value}</span>
                          </div>
                        ))}
                        <div className="pt-2 border-t flex justify-between text-sm">
                          <span className="text-gray-500">Total</span>
                          <span className="font-bold text-gray-900">
                            {pieData.reduce((s, d) => s + d.value, 0)}
                          </span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-60 text-gray-400 text-sm">Aucune alerte</div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* ══ Export des Alertes ═══════════════════════════════════════════ */}
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            {/* Toolbar */}
            <div className="px-5 py-4 border-b bg-gray-50 flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <AlertCircle size={18} className="text-red-500 shrink-0" />
                <h3 className="text-base font-semibold text-gray-900">Journal des Alertes</h3>
                <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
                  {filtered.length} alerte{filtered.length !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Search */}
              <div className="relative">
                <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
                <input
                  type="text" value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1) }}
                  placeholder="Rechercher…"
                  className="pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-44"
                />
              </div>

              {/* Format selector + export */}
              <div className="flex items-center gap-2">
                <select
                  value={exportFmt}
                  onChange={e => setExportFmt(e.target.value)}
                  className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="csv">CSV</option>
                  <option value="excel">Excel (.xlsx)</option>
                  <option value="pdf">PDF</option>
                </select>
                <button
                  onClick={handleExport}
                  disabled={loadingExport}
                  className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
                >
                  {loadingExport ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : exportFmt === 'pdf' ? (
                    <FileText size={15} />
                  ) : exportFmt === 'excel' ? (
                    <FileSpreadsheet size={15} />
                  ) : (
                    <Sheet size={15} />
                  )}
                  {loadingExport ? 'Export…' : `Exporter ${exportFmt.toUpperCase()}`}
                </button>
              </div>
            </div>

            {/* Table */}
            {pageData.length === 0 ? (
              <div className="py-12 text-center text-gray-400 text-sm">
                <AlertCircle size={32} className="mx-auto mb-2 opacity-20" />
                {search ? 'Aucun résultat pour cette recherche' : 'Aucune alerte enregistrée'}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Caméra</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Heure</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Frame</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Temps</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Risque</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Capture</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {pageData.map(al => {
                      const dt = al.created_at ? new Date(al.created_at) : null
                      const ok = dt && !isNaN(dt)
                      return (
                        <tr key={al._id} className="hover:bg-gray-50 transition">
                          <td className="px-4 py-3">
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full shrink-0"
                                style={{ background: TYPE_COLORS[al.event_type] || '#94a3b8' }} />
                              <span className="font-medium text-gray-900">
                                {EVENT_LABELS[al.event_type] || al.event_type}
                              </span>
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1.5 text-gray-600">
                              <Camera size={12} className="text-gray-400 shrink-0" />
                              <span className="truncate max-w-32">{al.video_title}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-600">
                            <div className="flex items-center gap-1">
                              <Clock size={11} className="text-gray-400" />
                              {ok ? dt.toLocaleDateString('fr-FR') : '—'}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                            {ok ? dt.toLocaleTimeString('fr-FR') : '—'}
                          </td>
                          <td className="px-4 py-3 text-gray-500">{al.frame_id}</td>
                          <td className="px-4 py-3 text-gray-500">{Number(al.timestamp).toFixed(1)}s</td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                              al.risk_level === 'high'   ? 'bg-red-100 text-red-700' :
                              al.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                                           'bg-blue-100 text-blue-700'
                            }`}>{al.risk_level}</span>
                          </td>
                          <td className="px-4 py-3">
                            {al.capture ? (
                              <img src={capture(al.capture)}
                                className="w-14 h-10 object-cover rounded border"
                                onError={e => { e.target.style.display = 'none' }} />
                            ) : <span className="text-gray-300 text-xs">—</span>}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination intelligente */}
            {totalPages > 1 && (
              <div className="px-5 py-3 border-t bg-gray-50 flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  Page {page} / {totalPages} · {filtered.length} résultat{filtered.length !== 1 ? 's' : ''}
                </span>
                <div className="flex items-center gap-1">
                  <button onClick={() => setPage(1)} disabled={page === 1}
                    className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 transition text-xs font-medium px-2">
                    «
                  </button>
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                    className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 transition">
                    <ChevronLeft size={16} />
                  </button>
                  {(() => {
                    const delta = 2
                    const pages = []
                    for (let i = 1; i <= totalPages; i++) {
                      if (i === 1 || i === totalPages || (i >= page - delta && i <= page + delta)) {
                        pages.push(i)
                      }
                    }
                    const result = []
                    let prev = null
                    for (const p of pages) {
                      if (prev && p - prev > 1) {
                        result.push(<span key={`ellipsis-${p}`} className="px-1 text-gray-400 text-xs">…</span>)
                      }
                      result.push(
                        <button key={p} onClick={() => setPage(p)}
                          className={`w-7 h-7 text-xs rounded-lg transition ${
                            page === p ? 'bg-blue-600 text-white' : 'hover:bg-gray-200 text-gray-600'
                          }`}>
                          {p}
                        </button>
                      )
                      prev = p
                    }
                    return result
                  })()}
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                    className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 transition">
                    <ChevronRight size={16} />
                  </button>
                  <button onClick={() => setPage(totalPages)} disabled={page === totalPages}
                    className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 transition text-xs font-medium px-2">
                    »
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
