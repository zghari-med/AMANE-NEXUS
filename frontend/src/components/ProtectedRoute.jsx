import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../context/authStore'

function isTokenExpired(token) {
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

export default function ProtectedRoute({ children, requiredRole = null }) {
  const { user, token, logout } = useAuthStore()

  if (!token || !user || isTokenExpired(token)) {
    if (token) logout()
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to="/" replace />
  }

  return children
}
