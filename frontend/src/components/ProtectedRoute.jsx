import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../context/authStore'

export default function ProtectedRoute({ children, requiredRole = null }) {
  const { user, token } = useAuthStore()

  if (!token || !user) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to="/" replace />
  }

  return children
}
