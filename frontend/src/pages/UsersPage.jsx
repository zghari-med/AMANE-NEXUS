import { useState, useEffect } from 'react'
import { Trash2, Shield, User, UserPlus, X, Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '../context/authStore'
import Sidebar from '../components/Sidebar'
import toast from 'react-hot-toast'

const API = 'http://localhost:5000'

export default function UsersPage() {
  const { token, user } = useAuthStore()
  const [users, setUsers]       = useState([])
  const [loading, setLoading]   = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [showPwd, setShowPwd]   = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', role: 'user' })

  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => { fetchUsers() }, [])

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
    if (uid === user?.id) { toast.error('Impossible de supprimer votre propre compte'); return }
    if (!confirm('Supprimer cet utilisateur ?')) return
    try {
      const r = await fetch(`${API}/api/users/${uid}`, { method: 'DELETE', headers })
      const d = await r.json()
      if (!r.ok) throw new Error(d.error)
      toast.success('Utilisateur supprimé')
      fetchUsers()
    } catch (e) { toast.error(e.message) }
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

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 overflow-auto">
        <div className="p-8 max-w-5xl">

          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Gestion des Utilisateurs</h1>
              <p className="text-gray-500 mt-1">{users.length} utilisateur{users.length !== 1 ? 's' : ''}</p>
            </div>
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              <UserPlus size={18} />
              Ajouter un utilisateur
            </button>
          </div>

          {/* Create form */}
          {showForm && (
            <div className="bg-white rounded-xl shadow-md p-6 mb-6 border-l-4 border-blue-500">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-semibold text-gray-900">Nouvel utilisateur</h2>
                <button onClick={() => setShowForm(false)} className="p-1 hover:bg-gray-100 rounded">
                  <X size={20} />
                </button>
              </div>
              <form onSubmit={handleCreate} className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nom complet</label>
                  <input
                    type="text"
                    value={form.full_name}
                    onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: Mohammed Alami"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nom d'utilisateur *</label>
                  <input
                    type="text"
                    value={form.username}
                    onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: malami"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="email@exemple.com"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mot de passe *</label>
                  <div className="relative">
                    <input
                      type={showPwd ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Minimum 6 caractères"
                      required
                    />
                    <button type="button" onClick={() => setShowPwd(!showPwd)}
                      className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600">
                      {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rôle</label>
                  <select
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="user">Utilisateur</option>
                    <option value="admin">Administrateur</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 text-sm font-medium"
                  >
                    {submitting ? 'Création...' : 'Créer l\'utilisateur'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Users table */}
          {loading ? (
            <div className="bg-white rounded-xl p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
            </div>
          ) : users.length === 0 ? (
            <div className="bg-white rounded-xl p-12 text-center">
              <User size={48} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Aucun utilisateur trouvé</p>
              <button onClick={() => setShowForm(true)} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                Créer le premier utilisateur
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Utilisateur</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Rôle</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Créé le</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map(u => (
                    <tr key={u._id} className="hover:bg-gray-50 transition">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${u.role === 'admin' ? 'bg-orange-500' : 'bg-blue-500'}`}>
                            {u.username?.[0]?.toUpperCase() || '?'}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{u.username}</p>
                            {u.full_name && <p className="text-xs text-gray-500">{u.full_name}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{u.email}</td>
                      <td className="px-6 py-4">
                        <select
                          value={u.role}
                          onChange={e => handleRoleChange(u._id, e.target.value)}
                          disabled={u._id === user?.id}
                          className={`text-xs font-semibold px-2 py-1 rounded-full border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                            u.role === 'admin'
                              ? 'bg-orange-100 text-orange-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          <option value="user">Utilisateur</option>
                          <option value="admin">Administrateur</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('fr-FR') : 'N/A'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {u._id !== user?.id && (
                          <button
                            onClick={() => handleDelete(u._id)}
                            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
                            title="Supprimer"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
