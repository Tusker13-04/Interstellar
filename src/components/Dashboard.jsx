import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';
import { getDashboardStats } from '../services/apiService';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const Dashboard = () => {
  const [cargoStatus, setCargoStatus] = useState(null);
  const [monthlyArrivals, setMonthlyArrivals] = useState(null);
  const [weightTrends, setWeightTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        console.log('Fetching dashboard data...');
        const data = await getDashboardStats();
        console.log('Dashboard data:', data);
        if (data && data.success) {
          processData(data);
        } else {
          throw new Error(data.error || 'Failed to load dashboard data');
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        setError(error.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();

    // Refresh data every 5 minutes
    const interval = setInterval(fetchDashboardData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const processData = (data) => {
    console.log('Processing data:', data);
    // Process cargo status distribution
    setCargoStatus({
      labels: ['In Storage', 'In Transit', 'Retrieved', 'Expired'],
      datasets: [{
        data: [
          data.inStorage || 0,
          data.inTransit || 0,
          data.retrieved || 0,
          data.expired || 0
        ],
        backgroundColor: [
          'rgba(54, 162, 235, 0.8)',   // Blue for storage
          'rgba(255, 206, 86, 0.8)',   // Yellow for transit
          'rgba(75, 192, 192, 0.8)',   // Green for retrieved
          'rgba(255, 99, 132, 0.8)'    // Red for expired
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(255, 99, 132, 1)'
        ],
        borderWidth: 1
      }]
    });

    // Process monthly arrivals
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December'];
    setMonthlyArrivals({
      labels: months,
      datasets: [{
        label: 'Cargo Count',
        data: data.monthlyArrivals || Array(12).fill(0),
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1
      }]
    });

    // Process weight trends
    setWeightTrends({
      labels: data.weightTrends?.labels || [],
      datasets: [{
        label: 'Total Mass (kg)',
        data: data.weightTrends?.data || [],
        borderColor: 'rgb(255, 159, 64)',
        backgroundColor: 'rgba(255, 159, 64, 0.5)',
        tension: 0.4,
        fill: true
      }]
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <div className="text-lg text-gray-600">
          <svg className="animate-spin h-8 w-8 mr-3 inline" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Loading dashboard data...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <div className="text-lg text-red-600 bg-red-50 p-4 rounded-lg border border-red-200">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold text-gray-800 mb-8">Cargo Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Cargo Status Distribution */}
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Cargo Status Distribution</h2>
          {cargoStatus && (
            <div className="h-[300px] relative">
              <Pie
                data={cargoStatus}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: 'bottom',
                      labels: {
                        padding: 20,
                        usePointStyle: true
                      }
                    },
                    tooltip: {
                      callbacks: {
                        label: (context) => {
                          const label = context.label || '';
                          const value = context.raw || 0;
                          const total = context.dataset.data.reduce((a, b) => a + b, 0);
                          const percentage = total ? Math.round((value / total) * 100) : 0;
                          return `${label}: ${value} (${percentage}%)`;
                        }
                      }
                    }
                  }
                }}
              />
            </div>
          )}
        </div>

        {/* Monthly Cargo Arrivals */}
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Monthly Cargo Arrivals</h2>
          {monthlyArrivals && (
            <div className="h-[300px] relative">
              <Bar
                data={monthlyArrivals}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false
                    },
                    tooltip: {
                      callbacks: {
                        label: (context) => `Count: ${context.raw}`
                      }
                    }
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: {
                        precision: 0
                      }
                    }
                  }
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Cargo Weight Trends */}
      <div className="bg-white p-6 rounded-lg shadow-lg">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Cargo Mass Trends</h2>
        {weightTrends && (
          <div className="h-[300px] relative">
            <Line
              data={weightTrends}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    display: false
                  },
                  tooltip: {
                    callbacks: {
                      label: (context) => `Mass: ${context.raw.toFixed(2)} kg`
                    }
                  }
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    title: {
                      display: true,
                      text: 'Total Mass (kg)'
                    }
                  },
                  x: {
                    title: {
                      display: true,
                      text: 'Date'
                    }
                  }
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard; 