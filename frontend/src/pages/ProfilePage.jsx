import { useState } from 'react'
import Sidebar from '../components/Sidebar'
import { useAuthStore } from '../context/authStore'
import { Lock, Eye, EyeOff, ShieldCheck, KeyRound, Mail, User, Shield } from 'lucide-react'
import toast from 'react-hot-toast'

import { API } from '../services/api'

export default function ProfilePage() {
  const { user, token } = useAuthStore()
  const headers = { Authorization: `Bearer ${token}` }

  const [newPwd,     setNewPwd]     = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [showNew,    setShowNew]    = useState(false)
  const [showConf,   setShowConf]   = useState(false)
  const [saving,     setSaving]     = useState(false)

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (newPwd.length < 6)     { toast.error('Mot de passe trop court (min. 6 caractères)'); return }
    if (newPwd !== confirmPwd) { toast.error('Les mots de passe ne correspondent pas'); return }
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/users/${user.id}/password`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: newPwd }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error || 'Erreur')
      toast.success('Mot de passe modifié avec succès !')
      setNewPwd(''); setConfirmPwd('')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const pwdStrength = newPwd.length === 0 ? 0
    : newPwd.length < 6  ? 1
    : newPwd.length < 9  ? 2
    : newPwd.length < 12 ? 3 : 4

  const strengthLabel = ['', 'Trop court', 'Acceptable', 'Bien', 'Fort'][pwdStrength]
  const strengthColor = ['', 'bg-red-400', 'bg-yellow-400', 'bg-blue-400', 'bg-green-500'][pwdStrength]
  const isAdmin = user?.role === 'admin'

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <div className="flex-1 overflow-auto">

        {/* Header */}
        <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-5">
            <h1 className="text-2xl font-bold text-gray-900">Mon Profil</h1>
          </div>
        </div>

        <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">

          {/* ── User info card ── */}
          <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">

            {/* Gradient header */}
            <div className={`px-8 py-4 ${
              isAdmin
                ? 'bg-gradient-to-r from-orange-500 to-orange-600'
                : 'bg-gradient-to-r from-blue-600 to-blue-700'
            }`}>
              <div className="flex items-center gap-5">
                <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center text-2xl font-bold text-white shadow-lg shrink-0">
                  {user?.username?.[0]?.toUpperCase() || '?'}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white leading-tight">
                    {user?.full_name || user?.username}
                  </h2>
                  {user?.full_name && (
                    <p className="text-white/70 text-sm mt-0.5">@{user?.username}</p>
                  )}
                  <span className="mt-2 inline-block px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide bg-white/20 text-white">
                    {isAdmin ? 'Administrateur' : 'Utilisateur'}
                  </span>
                </div>
              </div>
            </div>

            {/* Info rows — label + valeur sur la même ligne */}
            <div className="px-8 py-4 space-y-3">

              <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                <div className="w-9 h-9 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
                  <User size={16} className="text-blue-600" />
                </div>
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wide w-36 shrink-0">Nom d'utilisateur</p>
                <p className="text-sm font-semibold text-gray-900">@{user?.username}</p>
              </div>

              {user?.full_name && (
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className="w-9 h-9 rounded-lg bg-purple-100 flex items-center justify-center shrink-0">
                    <User size={16} className="text-purple-600" />
                  </div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide w-36 shrink-0">Nom complet</p>
                  <p className="text-sm font-semibold text-gray-900">{user.full_name}</p>
                </div>
              )}

              {user?.email && (
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className="w-9 h-9 rounded-lg bg-green-100 flex items-center justify-center shrink-0">
                    <Mail size={16} className="text-green-600" />
                  </div>
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wide w-36 shrink-0">Adresse e-mail</p>
                  <p className="text-sm font-semibold text-gray-900">{user.email}</p>
                </div>
              )}

              
            </div>
          </div>

          {/* ── Change password card ── */}
          <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
            <div className="px-8 py-5 border-b bg-gray-50 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center">
                <KeyRound size={17} className="text-slate-600" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-900">Changer le mot de passe</h3>
                <p className="text-xs text-gray-500">Minimum 6 caractères</p>
              </div>
            </div>

            <form onSubmit={handleChangePassword} className="px-8 py-6 space-y-4">

              {/* Deux champs côte à côte */}
              <div className="grid grid-cols-2 gap-4">

                {/* Nouveau mot de passe */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Nouveau mot de passe
                  </label>
                  <div className="relative">
                    <input
                      type={showNew ? 'text' : 'password'}
                      value={newPwd}
                      onChange={e => setNewPwd(e.target.value)}
                      className="w-full border border-gray-300 rounded-xl px-4 py-3 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="••••••••"
                      required
                    />
                    <button type="button" tabIndex={-1}
                      onClick={() => setShowNew(v => !v)}
                      className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600">
                      {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {newPwd.length > 0 && (
                    <div className="mt-2">
                      <div className="flex gap-1">
                        {[1,2,3,4].map(i => (
                          <div key={i} className={`h-1 flex-1 rounded-full transition-all ${
                            i <= pwdStrength ? strengthColor : 'bg-gray-200'
                          }`} />
                        ))}
                      </div>
                      <p className="text-xs mt-1 text-gray-400">{strengthLabel}</p>
                    </div>
                  )}
                </div>

                {/* Confirmer mot de passe */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Confirmer le mot de passe
                  </label>
                  <div className="relative">
                    <input
                      type={showConf ? 'text' : 'password'}
                      value={confirmPwd}
                      onChange={e => setConfirmPwd(e.target.value)}
                      className={`w-full border rounded-xl px-4 py-3 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        confirmPwd.length > 0 && confirmPwd !== newPwd
                          ? 'border-red-400 bg-red-50'
                          : 'border-gray-300'
                      }`}
                      placeholder="••••••••"
                      required
                    />
                    <button type="button" tabIndex={-1}
                      onClick={() => setShowConf(v => !v)}
                      className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600">
                      {showConf ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {confirmPwd.length > 0 && confirmPwd !== newPwd && (
                    <p className="text-xs text-red-500 mt-1">Ne correspondent pas</p>
                  )}
                  {confirmPwd.length > 0 && confirmPwd === newPwd && (
                    <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                      <ShieldCheck size={12} /> Confirmé
                    </p>
                  )}
                </div>
              </div>

              <button
                type="submit"
                disabled={saving || newPwd !== confirmPwd || newPwd.length < 6}
                className="w-full py-3 bg-slate-800 hover:bg-slate-900 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition flex items-center justify-center gap-2">
                {saving
                  ? <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Enregistrement…</>
                  : <><Lock size={15} /> Enregistrer le mot de passe</>
                }
              </button>
            </form>
          </div>

        </div>
      </div>
    </div>
  )
}
