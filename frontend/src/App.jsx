import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './context/authStore'
import { Toaster } from 'react-hot-toast'

// Pages
import LoginPage          from './pages/LoginPage'
import DashboardAdminPage from './pages/DashboardAdminPage'
import DashboardUserPage  from './pages/DashboardUserPage'
import AnalysisPage       from './pages/AnalysisPage'
import VideosPage         from './pages/VideosPage'
import StatisticsPage     from './pages/StatisticsPage'
import BenchmarksPage     from './pages/BenchmarksPage'
import TrendsPage         from './pages/TrendsPage'
import UsersPage          from './pages/UsersPage'

// Composants
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  const { user } = useAuthStore()

  return (
    <>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" /> : <LoginPage />} />

        <Route path="/" element={
          <ProtectedRoute>
            {user?.role === 'admin' ? <DashboardAdminPage /> : <DashboardUserPage />}
          </ProtectedRoute>
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

        <Route path="/benchmarks" element={
          <ProtectedRoute><BenchmarksPage /></ProtectedRoute>
        } />

        <Route path="/trends" element={
          <ProtectedRoute><TrendsPage /></ProtectedRoute>
        } />

        <Route path="/users" element={
          <ProtectedRoute><UsersPage /></ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  )
}

export default App
