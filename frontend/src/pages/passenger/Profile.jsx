import { useState, useEffect } from 'react'
import { User, Mail, Phone, Camera, MapPin, CreditCard } from 'lucide-react'
import Header from '../../components/layout/Header'
import Input from '../../components/common/Input'
import Button from '../../components/common/Button'
import Card from '../../components/common/Card'
import { useAuth } from '../../hooks/useAuth'
import { authService } from '../../services/auth.service'

export function PassengerProfile () {
  const { user, updateUser } = useAuth()
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
  })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (user) {
      setFormData({
        firstName: user.first_name || '',
        lastName: user.last_name || '',
        email: user.email || '',
        phone: user.phone || '',
      })
    }
  }, [user])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setSuccess(false)

    try {
      const updatedUser = await authService.updateProfile({
        first_name: formData.firstName,
        last_name: formData.lastName,
        phone: formData.phone,
      })
      updateUser(updatedUser)
      setSuccess(true)
    } catch (error) {
      console.error('Failed to update profile:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold mb-8">Profile</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Profile Picture */}
          <div>
            <Card>
              <div className="text-center">
                <div className="relative inline-block">
                  <div className="w-32 h-32 bg-primary-100 rounded-full flex items-center justify-center text-primary-600 text-4xl font-bold">
                    {user?.first_name?.[0]}{user?.last_name?.[0]}
                  </div>
                  <button className="absolute bottom-0 right-0 w-10 h-10 bg-primary-600 text-white rounded-full flex items-center justify-center hover:bg-primary-700">
                    <Camera size={18} />
                  </button>
                </div>
                <h3 className="mt-4 text-xl font-semibold">
                  {user?.first_name} {user?.last_name}
                </h3>
                <p className="text-gray-600">{user?.email}</p>
              </div>
            </Card>

            {/* Quick Stats */}
            <Card className="mt-6">
              <h3 className="font-semibold mb-4">Statistics</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Rides</span>
                  <span className="font-semibold">24</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Member Since</span>
                  <span className="font-semibold">Jan 2024</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Rating</span>
                  <span className="font-semibold">4.8 ⭐</span>
                </div>
              </div>
            </Card>
          </div>

          {/* Profile Form */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <h2 className="text-xl font-semibold mb-6">Personal Information</h2>
              
              {success && (
                <div className="bg-green-50 text-green-600 px-4 py-3 rounded-lg mb-6">
                  Profile updated successfully!
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Input
                    label="First Name"
                    icon={User}
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                  />
                  <Input
                    label="Last Name"
                    icon={User}
                    value={formData.lastName}
                    onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                  />
                </div>

                <Input
                  type="email"
                  label="Email Address"
                  icon={Mail}
                  value={formData.email}
                  disabled
                />

                <Input
                  type="tel"
                  label="Phone Number"
                  icon={Phone}
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />

                <Button type="submit" loading={loading}>
                  Save Changes
                </Button>
              </form>
            </Card>

            {/* Saved Addresses */}
            <Card>
              <h2 className="text-xl font-semibold mb-6">Saved Addresses</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <MapPin className="text-primary-600" size={20} />
                    <div>
                      <p className="font-medium">Home</p>
                      <p className="text-sm text-gray-600">123 Main St, City</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">Edit</Button>
                </div>
                <Button variant="outline" className="w-full">
                  Add New Address
                </Button>
              </div>
            </Card>

            {/* Payment Methods */}
            <Card>
              <h2 className="text-xl font-semibold mb-6">Payment Methods</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CreditCard className="text-primary-600" size={20} />
                    <div>
                      <p className="font-medium">Visa •••• 4242</p>
                      <p className="text-sm text-gray-600">Expires 12/25</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">Remove</Button>
                </div>
                <Button variant="outline" className="w-full">
                  Add Payment Method
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}