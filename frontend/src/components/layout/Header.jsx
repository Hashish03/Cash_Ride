import { Menu, User, LogOut, Bell } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function Header() {
  const [showMenu, setShowMenu] = useState(false)
  const { user, logout } = useAuth()

  return (
    <header className="bg-white shadow-sm border-b sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">C</span>
            </div>
            <span className="text-xl font-bold text-gray-900">CashRide</span>
          </Link>

          {/* Right side */}
          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-gray-100 rounded-lg relative">
              <Bell size={20} />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded-lg"
              >
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <User size={18} className="text-primary-600" />
                </div>
                <span className="hidden sm:block text-sm font-medium">
                  {user?.first_name}
                </span>
              </button>

              {showMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border py-2">
                  <Link
                    to="/profile"
                    className="flex items-center gap-2 px-4 py-2 hover:bg-gray-50"
                    onClick={() => setShowMenu(false)}
                  >
                    <User size={18} />
                    <span>Profile</span>
                  </Link>
                  <button
                    onClick={() => {
                      setShowMenu(false)
                      logout()
                    }}
                    className="flex items-center gap-2 px-4 py-2 hover:bg-gray-50 w-full text-left text-red-600"
                  >
                    <LogOut size={18} />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}