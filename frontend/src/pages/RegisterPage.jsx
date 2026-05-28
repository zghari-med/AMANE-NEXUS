import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../context/authStore'
import { User, Mail, Lock, Loader } from 'lucide-react'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: ''
  })
  const navigate = useNavigate()
  const { register, isLoading } = useAuthStore()

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (formData.password !== formData.confirmPassword) {
      toast.error('Les mots de passe ne correspondent pas')
      return
    }

    const success = await register(
      formData.email,
      formData.password,
      formData.username,
      formData.fullName
    )

    if (success) {
      toast.success('Compte créé avec succès! Veuillez vous connecter.')
      navigate('/login')
    } else {
      toast.error('Erreur lors de la création du compte')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-50 p-4">
      <div className="w-full max-w-md">
        <div className="card-glass p-8 animate-slideInUp">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-secondary flex items-center justify-center mx-auto mb-4 shadow-lg">
              <User className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Créer un compte</h1>
            <p className="text-gray-600">Rejoignez la plateforme</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nom d'utilisateur</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="votre_username"
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nom complet</label>
              <input
                type="text"
                name="fullName"
                value={formData.fullName}
                onChange={handleChange}
                placeholder="Votre Nom"
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 text-gray-400" size={20} />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="votre@email.com"
                  className="input-field pl-10"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Mot de passe</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 text-gray-400" size={20} />
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="input-field pl-10"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Confirmer le mot de passe</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 text-gray-400" size={20} />
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="input-field pl-10"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? <Loader size={20} className="animate-spin" /> : null}
              {isLoading ? 'Création...' : 'Créer un compte'}
            </button>
          </form>

          <div className="my-6 flex items-center gap-4">
            <div className="flex-1 h-px bg-gray-300"></div>
            <span className="text-gray-500 text-sm">Ou</span>
            <div className="flex-1 h-px bg-gray-300"></div>
          </div>

          <Link to="/login" className="w-full btn-secondary flex items-center justify-center">
            Se connecter
          </Link>
        </div>
      </div>
    </div>
  )
}
