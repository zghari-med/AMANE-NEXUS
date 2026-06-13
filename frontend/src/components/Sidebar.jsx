import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Menu, X, LayoutDashboard, Video, BarChart3,
  LogOut, Users, UserCircle, Shield,
} from 'lucide-react'
import { useAuthStore } from '../context/authStore'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true)
  const { user, logout }    = useAuthStore()
  const location            = useLocation()

  const isActive = (href) =>
    href === '/' ? location.pathname === '/' : location.pathname.startsWith(href)

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard',    href: '/'           },
    { icon: Video,           label: 'Vidéos',       href: '/videos'     },
    { icon: BarChart3,       label: 'Statistiques', href: '/statistics' },
    { icon: UserCircle,      label: 'Mon Profil',   href: '/profile'    },
  ]

  const NavLink = ({ item }) => {
    const active = isActive(item.href)
    return (
      <Link
        to={item.href}
        className={`nav-link ${active ? 'nav-link-active' : ''}`}
      >
        <item.icon
          size={18}
          className={active ? 'text-brand-600' : 'text-secondaryGray-600'}
        />
        <span>{item.label}</span>
        {active && (
          <div className="ml-auto w-1.5 h-5 rounded-full bg-brand-600" />
        )}
      </Link>
    )
  }

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-4 left-4 z-40 p-2 bg-white rounded-xl shadow-horizon lg:hidden"
      >
        {isOpen ? <X size={20} className="text-navy-700" /> : <Menu size={20} className="text-navy-700" />}
      </button>

      {/* Sidebar */}
      <div className={`
        fixed left-0 top-0 h-screen w-64 bg-white shadow-horizon
        flex flex-col z-30 transition-transform duration-300
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:static
      `}>

        {/* Logo */}
        <div className="px-6 pt-8 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-brand flex items-center justify-center shadow-sm">
              <Shield size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-navy-700 leading-tight">AMANE</h1>
              <p className="text-[10px] text-secondaryGray-600 font-medium tracking-wide">NEXUS PLATFORM</p>
            </div>
          </div>
        </div>

        {/* Section label */}
        <div className="px-6 mb-2">
          <p className="text-[10px] uppercase font-semibold tracking-widest text-secondaryGray-600">
            Navigation
          </p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
          {menuItems.map(item => <NavLink key={item.href} item={item} />)}

          {user?.role === 'admin' && (
            <>
              <div className="px-4 pt-5 pb-2">
                <p className="text-[10px] uppercase font-semibold tracking-widest text-secondaryGray-600">
                  Administration
                </p>
              </div>
              <NavLink item={{ icon: Users, label: 'Utilisateurs', href: '/users' }} />
            </>
          )}
        </nav>

        {/* User card + logout */}
        <div className="p-4 mx-3 mb-4 rounded-2xl bg-secondaryGray-300">
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold text-white flex-shrink-0 ${
              user?.role === 'admin' ? 'bg-gradient-brand' : 'bg-navy-600'
            }`}>
              {user?.username?.[0]?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-navy-700 truncate">{user?.username}</p>
              <p className="text-[11px] text-secondaryGray-600 font-medium capitalize">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-secondaryGray-600 hover:text-red-500 hover:bg-red-50 transition-all text-xs font-medium"
          >
            <LogOut size={14} />
            <span>Déconnexion</span>
          </button>
        </div>
      </div>

      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-navy-900/30 backdrop-blur-sm z-20 lg:hidden" onClick={() => setIsOpen(false)} />
      )}
    </>
  )
}
