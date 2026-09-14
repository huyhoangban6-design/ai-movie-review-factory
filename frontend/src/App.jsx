import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import AuthView from './views/AuthView'
import DashboardView from './views/DashboardView'
import ProjectDetailView from './views/ProjectDetailView'

function Shell({ children }) {
  const { user, logout } = useAuth()
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">AI Movie Review Factory</div>
        {user && (
          <div className="topbar-right">
            <span className="user-chip">{user.display_name}</span>
            <button className="btn btn-ghost" onClick={logout} type="button">
              Đăng xuất
            </button>
          </div>
        )}
      </header>
      <main className="content">{children}</main>
    </div>
  )
}

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="page-loading">Đang tải…</div>
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}

export default function App() {
  const { loading } = useAuth()
  if (loading) return <div className="page-loading">Đang tải…</div>
  return (
    <Routes>
      <Route path="/login" element={<AuthView />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Shell>
              <Routes>
                <Route index element={<DashboardView />} />
                <Route path="projects/:id" element={<ProjectDetailView />} />
              </Routes>
            </Shell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}