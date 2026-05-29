import { useState, useEffect } from 'react'
import { Trash2, User, UserPlus, X, Eye, EyeOff, KeyRound, Activity, ChevronLeft, ChevronRight, LogIn, LogOut, Upload, Play, Trash, Settings, Clock } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import toast from 'react-hot-toast'

import { API } from '../services/api'

const ACTION_META = {
  LOGIN:           { label: 'Connexion',         color: 'bg-green-100 text-green-700',  icon: LogIn    },
  LOGOUT:          { label: 'Déconnexion',        color: 'bg-gray-100 text-gray-600',    icon: LogOut   },
  UPLOAD_VIDEO:    { label: 'Upload vidéo',       color: 'bg-blue-100 text-blue-700',    icon: Upload   },
  CREATE_ANALYSIS: { label: 'Analyse lancée',     color: 'bg-purple-100 text-purple-700',icon: Play     },
  DELETE_VIDEO:    { label: 'Vidéo supprimée',    color: 'bg-red-100 text-red-700',      icon: Trash    },
  CREATE_USER:     { label: 'Utilisateur créé',   color: 'bg-teal-100 text-teal-700',    icon: UserPlus },
  DELETE_USER:     { label: 'Utilisateur supprimé',color:'bg-red-100 text-red-700',      icon: Trash    },
  CHANGE_PASSWORD: { label: 'Mot de passe modifié',color:'bg-yellow-100 text-yellow-700',icon: KeyRound },
}

export default function UsersPage() {
  const { token, user: currentUser } = useAuthStore()
  const [tab, setTab] = useState('users')   // 'users' | 'logs'

  const [users, setUsers]       = useState([])
  const [loading, setLoading]   = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [showPwd, setShowPwd]   = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Logs state
  const [logs,      setLogs]      = useState([])
  const [logsTotal, setLogsTotal] = useState(0)
  const [logsPage,  setLogsPage]  = useState(1)
  const [logsLoading, setLogsLoading] = useState(false)
  const LOGS_PER_PAGE = 15
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', role: 'user' })

  // Password change modal state
  const [pwdModal, setPwdModal]   = useState(null)   // user object being edited
  const [newPwd, setNewPwd]       = useState('')
  const [showNewPwd, setShowNewPwd] = useState(false)
  const [pwdLoading, setPwdLoading] = useState(false)

  // Delete confirmation modal
  const [confirmDelete, setConfirmDelete] = useState(null) // user object to delete

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => { fetchUsers() }, [])
  useEffect(() => { if (tab === 'logs') fetchLogs(logsPage) }, [tab, logsPage])

  const fetchLogs = async (p = 1) => {
    setLogsLoading(true)
    try {
      const r = await fetch(`${API}/api/activity-logs?page=${p}&limit=${LOGS_PER_PAGE}`, { headers })
      if (!r.ok) return
      const d = await r.json()
      setLogs(d.logs || [])
      setLogsTotal(d.total || 0)
    } catch { /* ignore */ }
    finally { setLogsLoading(false) }
  }

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/users`, { headers })
      if (!r.ok) throw new Error()
      const d = await r.json()
      setUsers(d.users || [])
    } catch {
      toast.error('Erreur chargement utilisateurs')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.username || !form.email || !form.password) {
      toast.error('Remplissez tous les champs obligatoires')
      return
    }
    setSubmitting(true)
    try {
      const r = await fetch(`${API}/api/users`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      toast.success('Utilisateur créé !')
      setForm({ username: '', email: '', password: '', full_name: '', role: 'user' })
      setShowForm(false)
      fetchUsers()
    } catch (e) {
      toast.error(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (uid) => {
    if (uid === currentUser?.id) { toast.error('Impossible de supprimer votre propre compte'); return }
    const target = users.find(u => u._id === uid)
    setConfirmDelete(target)
  }

  const confirmDeleteUser = async () => {
    if (!confirmDelete) return
    try {
      const r = await fetch(`${API}/api/users/${confirmDelete._id}`, { method: 'DELETE', headers })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error)
      toast.success('Utilisateur supprimé')
      setConfirmDelete(null)
      fetchUsers()
    } catch (e) {
      toast.error(e.message)
      setConfirmDelete(null)
    }
  }

  const handleRoleChange = async (uid, newRole) => {
    try {
      const r = await fetch(`${API}/api/users/${uid}`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      })
      if (!r.ok) throw new Error()
      toast.success('Rôle mis à jour')
      fetchUsers()
    } catch { toast.error('Erreur mise à jour') }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (!newPwd || newPwd.length < 6) {
      toast.error('Mot de passe trop court (minimum 6 caractères)')
      return
    }
    setPwdLoading(true)
    try {
      const r = await fetch(`${API}/api/users/${pwdModal._id}/password`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: newPwd }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      toast.success(`Mot de passe de "${pwdModal.username}" modifié !`)
      setPwdModal(null)
      setNewPwd('')
    } catch (e) {
      toast.error(e.message)
    } finally {
      setPwdLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      {/* Password change modal */}
      {pwdModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center">
                  <KeyRound size={18} className="text-white" />
                </div>
                <div>
                  <h2 className="text-white font-semibold">Changer le mot de passe</h2>
                  <p className="text-blue-200 text-xs">Utilisateur : {pwdModal.username}</p>
                </div>
              </div>
              <button onClick={() => { setPwdModal(null); setNewPwd('') }}
                className="text-white/70 hover:text-white transition p-1 rounded-lg hover:bg-white/10">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handlePasswordChange} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nouveau mot de passe
                </label>
                <div className="relative">
                  <input
                    type={showNewPwd ? 'text' : 'password'}
                    value={newPwd}
                    onChange={e => setNewPwd(e.target.value)}
                    className="w-full border border-gray-300 rounded-xl px-4 py-3 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Minimum 6 caractères"
                    autoFocus
                    required
                  />
                  <button type="button" onClick={() => setShowNewPwd(!showNewPwd)}
                    className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600">
                    {showNewPwd ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
                {newPwd.length > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex gap-1 flex-1">
                      {[...Array(4)].map((_, i) => (
                        <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${
                          newPwd.length >= (i + 1) * 3 ? (newPwd.length >= 10 ? 'bg-green-500' : 'bg-yellow-400') : 'bg-gray-200'
                        }`} />
                      ))}
                    </div>
                    <span className="text-xs text-gray-500">
                      {newPwd.length < 6 ? 'Trop court' : newPwd.length < 10 ? 'Moyen' : 'Fort'}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => { setPwdModal(null); setNewPwd('') }}
                  className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition text-sm font-medium"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={pwdLoading || newPwd.length < 6}
                  className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-50 text-sm font-medium"
                >
                  {pwdLoading ? 'Modification…' : 'Confirmer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
            <div className="bg-gradient-to-r from-red-500 to-red-600 px-6 py-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center shrink-0">
                <Trash2 size={18} className="text-white" />
              </div>
              <div>
                <h2 className="text-white font-semibold">Confirmer la suppression</h2>
                <p className="text-red-200 text-xs">Cette action est irréversible</p>
              </div>
            </div>
            <div className="p-6">
              <p className="text-gray-700 text-sm mb-1">
                Voulez-vous vraiment supprimer l'utilisateur&nbsp;:
              </p>
              <p className="font-bold text-gray-900 text-base mb-5">
                {confirmDelete.full_name
                  ? `${confirmDelete.full_name} (@${confirmDelete.username})`
                  : `@${confirmDelete.username}`}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setConfirmDelete(null)}
                  className="flex-1 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition text-sm font-medium"
                >
                  Annuler
                </button>
                <button
                  onClick={confirmDeleteUser}
                  className="flex-1 py-2.5 bg-red-600 text-white rounded-xl hover:bg-red-700 transition text-sm font-semibold"
                >
                  Supprimer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {/* Sticky header with tabs */}
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 pt-5 pb-0 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Gestion des Utilisateurs</h1>
            </div>
            {tab === 'users' && (
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
            >
              <UserPlus size={17} />
              Ajouter un utilisateur
            </button>
            )}
          </div>
          {/* Tab bar */}
          <div className="max-w-7xl mx-auto px-6 flex gap-1 mt-3">
            {[
              { id: 'users', label: 'Utilisateurs', icon: User },
              { id: 'logs',  label: 'Journal d\'activité', icon: Activity },
            ].map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setTab(id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
                  tab === id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}>
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">

          {/* Create form */}
          {/* ══ TAB: Journal d'activité ══════════════════════════════════════ */}
          {tab === 'logs' && (
            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50 flex items-center gap-3">
                <Activity size={18} className="text-blue-600" />
                <h3 className="text-base font-semibold text-gray-900">Journal d'activité</h3>
                <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full ml-auto">
                  {logsTotal} événements
                </span>
                <button onClick={() => fetchLogs(logsPage)}
                  className="text-xs text-blue-600 hover:underline">↻ Rafraîchir</button>
              </div>

              {logsLoading ? (
                <div className="py-12 flex items-center justify-center">
                  <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
                </div>
              ) : logs.length === 0 ? (
                <div className="py-12 text-center text-gray-400 text-sm">
                  <Activity size={32} className="mx-auto mb-2 opacity-20" />
                  Aucune activité enregistrée
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 border-b">
                        <tr>
                          <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date / Heure</th>
                          <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Utilisateur</th>
                          <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Action</th>
                          <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Détails</th>
                          <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">IP</th>
                          <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Statut</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {logs.map(l => {
                          const meta = ACTION_META[l.action] || { label: l.action, color: 'bg-gray-100 text-gray-600', icon: Settings }
                          const Icon = meta.icon
                          const dt = l.created_at ? new Date(l.created_at) : null
                          const ok = dt && !isNaN(dt)
                          return (
                            <tr key={l._id} className="hover:bg-gray-50 transition">
                              <td className="px-5 py-3 whitespace-nowrap">
                                <div className="flex items-center gap-1.5">
                                  <Clock size={12} className="text-gray-400 shrink-0" />
                                  <div>
                                    <div className="text-xs text-gray-700 font-medium">
                                      {ok ? dt.toLocaleDateString('fr-FR') : '—'}
                                    </div>
                                    <div className="text-[10px] text-gray-400 font-mono">
                                      {ok ? dt.toLocaleTimeString('fr-FR') : ''}
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td className="px-5 py-3">
                                <div className="flex items-center gap-2">
                                  <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-white text-xs font-bold shrink-0">
                                    {l.username?.[0]?.toUpperCase() || '?'}
                                  </div>
                                  <span className="text-sm font-medium text-gray-800">{l.username}</span>
                                </div>
                              </td>
                              <td className="px-5 py-3">
                                <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${meta.color}`}>
                                  <Icon size={11} />
                                  {meta.label}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-gray-600 text-sm max-w-xs truncate">{l.details || '—'}</td>
                              <td className="px-5 py-3 text-gray-400 text-xs font-mono">{l.ip || '—'}</td>
                              <td className="px-5 py-3">
                                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                                  l.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>{l.status}</span>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                  {/* Pagination */}
                  {Math.ceil(logsTotal / LOGS_PER_PAGE) > 1 && (
                    <div className="px-5 py-3 border-t bg-gray-50 flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        Page {logsPage} / {Math.ceil(logsTotal / LOGS_PER_PAGE)}
                      </span>
                      <div className="flex gap-1">
                        <button onClick={() => setLogsPage(p => Math.max(1, p-1))} disabled={logsPage===1}
                          className="p-1.5 rounded hover:bg-gray-200 disabled:opacity-30"><ChevronLeft size={15}/></button>
                        <button onClick={() => setLogsPage(p => Math.min(Math.ceil(logsTotal/LOGS_PER_PAGE), p+1))}
                          disabled={logsPage === Math.ceil(logsTotal/LOGS_PER_PAGE)}
                          className="p-1.5 rounded hover:bg-gray-200 disabled:opacity-30"><ChevronRight size={15}/></button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ══ TAB: Utilisateurs ═══════════════════════════════════════════ */}
          {tab === 'users' && showForm && (
            <div className="bg-white rounded-xl shadow-sm border border-blue-200 overflow-hidden">
              <div className="bg-blue-50 border-b border-blue-100 px-6 py-4 flex items-center justify-between">
                <h2 className="text-base font-semibold text-blue-900 flex items-center gap-2">
                  <UserPlus size={17} /> Nouvel utilisateur
                </h2>
                <button onClick={() => setShowForm(false)} className="p-1 hover:bg-blue-100 rounded-lg transition">
                  <X size={18} className="text-blue-600" />
                </button>
              </div>
              <form onSubmit={handleCreate} className="p-6 grid grid-cols-2 gap-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Nom complet</label>
                  <input
                    type="text"
                    value={form.full_name}
                    onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: Mohammed Alami"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Nom d'utilisateur *</label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: malami"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Email *</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="email@exemple.com"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Mot de passe *</label>
                  <div className="relative">
                    <input
                      type={showPwd ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Minimum 6 caractères"
                      required
                    />
                    <button type="button" onClick={() => setShowPwd(!showPwd)}
                      className="absolute right-3 top-3 text-gray-400 hover:text-gray-600">
                      {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Rôle</label>
                  <select
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="user">Utilisateur</option>
                    <option value="admin">Administrateur</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 text-sm font-medium"
                  >
                    {submitting ? 'Création…' : 'Créer l\'utilisateur'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Users table — only when tab === 'users' */}
          {tab === 'users' && (loading ? (
            <div className="bg-white rounded-xl p-12 text-center border">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
            </div>
          ) : users.length === 0 ? (
            <div className="bg-white rounded-xl p-12 text-center border">
              <User size={48} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 mb-4">Aucun utilisateur trouvé</p>
              <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                Créer le premier utilisateur
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Utilisateur</th>
                    <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Email</th>
                    <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Rôle</th>
                    <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Créé le</th>
                    <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map(u => (
                    <tr key={u._id} className="hover:bg-gray-50 transition">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${u.role === 'admin' ? 'bg-orange-500' : 'bg-blue-500'}`}>
                            {u.username?.[0]?.toUpperCase() || '?'}
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{u.username}</p>
                            {u.full_name && <p className="text-xs text-gray-500">{u.full_name}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{u.email}</td>
                      <td className="px-6 py-4">
                        <select
                          value={u.role}
                          onChange={e => handleRoleChange(u._id, e.target.value)}
                          disabled={u._id === currentUser?.id}
                          className={`text-xs font-semibold px-2.5 py-1 rounded-full border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            u.role === 'admin' ? 'bg-orange-100 text-orange-800' : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          <option value="user">Utilisateur</option>
                          <option value="admin">Administrateur</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('fr-FR') : 'N/A'}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-center gap-2">
                          {/* Change password */}
                          <button
                            onClick={() => { setPwdModal(u); setNewPwd(''); setShowNewPwd(false) }}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition"
                            title="Changer le mot de passe"
                          >
                            <KeyRound size={13} />
                            Mot de passe
                          </button>
                          {/* Delete */}
                          {u._id !== currentUser?.id && (
                            <button
                              onClick={() => handleDelete(u._id)}
                              className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition"
                              title="Supprimer"
                            >
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
