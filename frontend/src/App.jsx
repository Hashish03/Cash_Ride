import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

// Auth Pages
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'

// Passenger Pages
import { PassengerHome } from './pages/passenger/Home'
import { BookRide } from './pages/passenger/BookRide'
import { RideTracking } from './pages/passenger/RideTracking'
import { PassengerProfile } from './pages/passenger/Profile'

// Driver Pages
import { DriverDashboard } from './pages/driver/Dashboard'
import { AcceptRide } from './pages/driver/AcceptRide'
import { Earnings } from './pages/driver/Earnings'



// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user?.user_type)) {
    return <Navigate to="/" replace />
  }

  return children
}

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Passenger Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute allowedRoles={['passenger']}>
              <PassengerHome />
            </ProtectedRoute>
          }
        />
        <Route
          path="/book-ride"
          element={
            <ProtectedRoute allowedRoles={['passenger']}>
              <BookRide />
            </ProtectedRoute>
          }
        />
        <Route
          path="/ride/:rideId"
          element={
            <ProtectedRoute allowedRoles={['passenger']}>
              <RideTracking />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute allowedRoles={['passenger']}>
              <PassengerProfile />
            </ProtectedRoute>
          }
        />

        {/* Driver Routes */}
        <Route
          path="/driver/dashboard"
          element={
            <ProtectedRoute allowedRoles={['driver']}>
              <DriverDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/driver/ride/:rideId"
          element={
            <ProtectedRoute allowedRoles={['driver']}>
              <AcceptRide />
            </ProtectedRoute>
          }
        />
        <Route
          path="/driver/earnings"
          element={
            <ProtectedRoute allowedRoles={['driver']}>
              <Earnings />
            </ProtectedRoute>
          }
        />

        
      </Routes>
    </Router>
  )
}