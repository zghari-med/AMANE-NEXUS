import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './context/authStore'
import { Toaster } from 'react-hot-toast'

// Pages
import LoginPage          from './pages/LoginPage'
import DashboardAdminPage from './pages/DashboardAdminPage'
import AnalysisPage       from './pages/AnalysisPage'
import VideosPage         from './pages/VideosPage'
import StatisticsPage     from './pages/StatisticsPage'
import UsersPage          from './pages/UsersPage'
import ProfilePage        from './pages/ProfilePage'

// Composants
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  const { user } = useAuthStore()

  return (
    <>
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            zIndex: 99999,
            fontFamily: 'Inter, sans-serif',
            fontSize: '14px',
            fontWeight: 500,
            borderRadius: '10px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
            padding: '12px 18px',
          },
          success: { style: { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' } },
          error:   { style: { background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' } },
        }}
      />
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage />} />

        <Route path="/" element={
          <ProtectedRoute><DashboardAdminPage /></ProtectedRoute>
        } />

        <Route path="/analysis/:analysisId" element={
          <ProtectedRoute><AnalysisPage /></ProtectedRoute>
        } />

        <Route path="/videos" element={
          <ProtectedRoute><VideosPage /></ProtectedRoute>
        } />

        <Route path="/statistics" element={
          <ProtectedRoute><StatisticsPage /></ProtectedRoute>
        } />

<Route path="/users" element={
          <ProtectedRoute requiredRole="admin"><UsersPage /></ProtectedRoute>
        } />

        <Route path="/profile" element={
          <ProtectedRoute><ProfilePage /></ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  )
}

export default App
