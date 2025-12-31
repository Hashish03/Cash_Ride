import { useState } from 'react'
import { DollarSign, TrendingUp, Calendar } from 'lucide-react'
import Header from '../../components/layout/Header'
import Card from '../../components/common/Card'

export default function Earnings() {
  const [period, setPeriod] = useState('week')

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold mb-8">Earnings</h1>

        {/* Period Selector */}
        <div className="flex gap-2 mb-8">
          {['day', 'week', 'month', 'year'].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                period === p
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <DollarSign className="text-green-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Earnings</p>
                <p className="text-2xl font-bold">$2,450</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="text-blue-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Trips</p>
                <p className="text-2xl font-bold">87</p>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <Calendar className="text-purple-600" size={24} />
              </div>
              <div>
                <p className="text-sm text-gray-600">Avg per Trip</p>
                <p className="text-2xl font-bold">$28.16</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Earnings Chart Placeholder */}
        <Card>
          <h2 className="text-xl font-semibold mb-6">Earnings Overview</h2>
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
            <p className="text-gray-500">Chart will be displayed here</p>
          </div>
        </Card>

        {/* Recent Transactions */}
        <Card className="mt-8">
          <h2 className="text-xl font-semibold mb-6">Recent Transactions</h2>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium">Ride #{1000 + i}</p>
                  <p className="text-sm text-gray-600">Dec {i}, 2024 • 2.5 km</p>
                </div>
                <p className="text-lg font-bold text-green-600">+$25.00</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}