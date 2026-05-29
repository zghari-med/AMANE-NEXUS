import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Menu, X, LayoutDashboard, Video, BarChart3,
  LogOut, Users, UserCircle,
} from 'lucide-react'
import { useAuthStore } from '../context/authStore'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true)
  const { user, logout }    = useAuthStore()
  const location            = useLocation()

  const isActive = (href) =>
    href === '/' ? location.pathname === '/' : location.pathname.startsWith(href)

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard',    href: '/',           color: 'text-blue-400'   },
    { icon: Video,           label: 'Vidéos',       href: '/videos',     color: 'text-purple-400' },
    { icon: BarChart3,       label: 'Statistiques', href: '/statistics', color: 'text-green-400'  },
    { icon: UserCircle,      label: 'Mon Profil',   href: '/profile',    color: 'text-pink-400'   },
  ]

  const NavLink = ({ item }) => (
    <Link
      to={item.href}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all
        ${isActive(item.href) ? 'bg-slate-700 shadow-sm' : 'hover:bg-slate-700/60'}`}
    >
      <item.icon size={18} className={item.color} />
      <span className="text-sm font-medium">{item.label}</span>
      {isActive(item.href) && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400" />}
    </Link>
  )

  return (
    <>
      {/* Mobile Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-40 p-2 bg-white rounded-lg shadow-md lg:hidden"
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Sidebar */}
      <div className={`
        fixed left-0 top-0 h-screen w-60 bg-gradient-to-b from-slate-900 to-slate-800
        text-white shadow-2xl transition-transform duration-300 flex flex-col
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:static z-30
      `}>
        {/* Logo */}
        <div className="p-5 border-b border-slate-700 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
              <Video size={20} className="text-white" />
            </div>
            <h1 className="text-lg font-bold leading-tight">AMANE-NEXUS</h1>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">

          {/* Common links — everyone */}
          {menuItems.map(item => <NavLink key={item.href} item={item} />)}

          {/* Admin-only section */}
          {user?.role === 'admin' && (
            <>
              <div className="px-3 pt-4 pb-1">
                <p className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider">
                  Administration
                </p>
              </div>
              <NavLink item={{ icon: Users, label: 'Utilisateurs', href: '/users', color: 'text-orange-400' }} />
            </>
          )}
        </nav>

        {/* User info + logout */}
        <div className="p-3 border-t border-slate-700 shrink-0 space-y-2">
          <div className="px-3 py-2.5 rounded-lg bg-slate-700/40">
            <div className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                user?.role === 'admin' ? 'bg-orange-500' : 'bg-blue-500'
              }`}>
                {user?.username?.[0]?.toUpperCase() || '?'}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{user?.username}</p>
                <p className="text-xs text-slate-400 uppercase">{user?.role}</p>
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors text-sm"
          >
            <LogOut size={16} />
            <span>Déconnexion</span>
          </button>
        </div>
      </div>

      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-20 lg:hidden" onClick={() => setIsOpen(false)} />
      )}
    </>
  )
}
