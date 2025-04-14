import { useEffect, useState } from "react";
import SideNavBar from "../components/dashboard/sideNavBar";
import { Card, CardContent, Typography, CircularProgress, Button } from "@mui/material";
import { BarChart, Bar, PieChart, Pie, LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell } from "recharts";
import { getDashboardStats } from "../services/apiService";

const Home = () => {
  const [containerData, setContainerData] = useState(null);
  const [cargoArrivals, setCargoArrivals] = useState(null);
  const [weightTrends, setWeightTrends] = useState(null);
  const [cargoStatus, setCargoStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [noData, setNoData] = useState(false);

  // Colors for different container states
  const CONTAINER_COLORS = ['#0088FE', '#00C49F', '#FF8042'];
  
  // Status card colors
  const STATUS_COLORS = {
    'In Storage': { bg: 'bg-gray-800', text: 'text-blue-400', border: 'border-blue-900' },
    'In Transit': { bg: 'bg-gray-800', text: 'text-yellow-400', border: 'border-yellow-900' },
    'Retrieved': { bg: 'bg-gray-800', text: 'text-green-400', border: 'border-green-900' },
    'Expired': { bg: 'bg-gray-800', text: 'text-red-400', border: 'border-red-900' }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      setNoData(false);
      
      const data = await getDashboardStats();
      
      if (data && data.success) {
        // Transform container fullness data for pie chart
        // Filter out zero values to avoid empty segments
        const containerItems = [
          { name: 'Full Containers', value: data.fullContainers },
          { name: 'Partially Full Containers', value: data.partiallyFullContainers },
          { name: 'Empty Containers', value: data.emptyContainers }
        ].filter(item => item.value > 0);
        
        setContainerData(containerItems.length > 0 ? containerItems : null);

        // Create cargo status data for the cards
        setCargoStatus([
          { status: 'In Storage', count: data.inStorage },
          { status: 'In Transit', count: data.inTransit },
          { status: 'Retrieved', count: data.retrieved },
          { status: 'Expired', count: data.expired }
        ]);

        // Transform data for bar chart
        const shortMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        setCargoArrivals(
          shortMonths.map((month, index) => ({
            month,
            count: data.monthlyArrivals[index]
          }))
        );

        // Transform data for line chart
        setWeightTrends(
          data.weightTrends.labels.map((date, index) => ({
            date,
            weight: data.weightTrends.data[index]
          }))
        );
      } else if (data && data.error === "No imported items data found") {
        // Items haven't been imported yet
        setNoData(true);
        setContainerData(null);
        setCargoStatus(null);
        setCargoArrivals(null);
        setWeightTrends(null);
      } else {
        throw new Error(data?.error || 'Failed to load dashboard data');
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      setError(error.message);
      setContainerData(null);
      setCargoStatus(null);
      setCargoArrivals(null);
      setWeightTrends(null);
    } finally {
      setLoading(false);
    }
  };

  // Custom pie chart tooltip to show percentages
  const ContainerTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const total = containerData.reduce((sum, item) => sum + item.value, 0);
      const percentage = total > 0 ? ((data.value / total) * 100).toFixed(1) : 0;
      
      return (
        <div className="bg-white p-2 shadow-md rounded-md border border-gray-200">
          <p className="font-semibold">{`${data.name}: ${data.value}`}</p>
          <p>{`${percentage}%`}</p>
        </div>
      );
    }
    return null;
  };

  useEffect(() => {
    fetchData();

    // Refresh data every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <CircularProgress />
      </div>
    );
  }

  return (
    <div className="flex">
      <div className="hidden md:block md:w-64 bg-slate-50 h-screen fixed">
        <SideNavBar />
      </div>
      <div className="flex-1 p-6 ml-64">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md flex justify-between items-center">
            <span>Error: {error}</span>
            <Button 
              variant="outlined" 
              color="error" 
              size="small" 
              onClick={fetchData}
            >
              Retry
            </Button>
          </div>
        )}
        
        {noData && (
          <div className="mb-4 p-6 bg-blue-50 border border-blue-200 text-blue-700 rounded-md">
            <h2 className="text-xl font-semibold mb-2">No cargo data available yet</h2>
            <p className="mb-4">Please import items and containers to see dashboard visualizations.</p>
            <p>You can import data from the Import/Export section in the navigation menu.</p>
          </div>
        )}
      
        {cargoStatus && (
          <>
            <div className="grid grid-cols-4 gap-4 mb-6">
              {cargoStatus.map((item) => (
                <Card 
                  key={item.status} 
                  className={`p-4 border ${STATUS_COLORS[item.status].border} shadow-lg`} 
                  sx={{ backgroundColor: '#1f2937' }}
                >
                  <CardContent sx={{ padding: '0 !important' }}>
                    <Typography variant="h6" className={STATUS_COLORS[item.status].text}>{item.status}</Typography>
                    <Typography variant="h4" className={`font-bold ${STATUS_COLORS[item.status].text}`}>{item.count}</Typography>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="p-4 bg-gray-800 shadow-lg rounded-lg">
                <Typography variant="h6" className="mb-2 text-white">Container Fullness</Typography>
                {containerData && containerData.reduce((sum, item) => sum + item.value, 0) > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie 
                        data={containerData} 
                        dataKey="value" 
                        nameKey="name" 
                        cx="50%" 
                        cy="50%" 
                        outerRadius={80} 
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {containerData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={CONTAINER_COLORS[index % CONTAINER_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip content={<ContainerTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-gray-400">
                    No container data available
                  </div>
                )}
              </div>

              <div className="p-4 bg-gray-800 shadow-lg rounded-lg">
                <Typography variant="h6" className="mb-2 text-white">Monthly Cargo Arrivals</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={cargoArrivals}>
                    <XAxis 
                      dataKey="month" 
                      tick={{ fontSize: 12, fill: '#fff' }}
                      height={50}
                      angle={-30}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis tick={{ fill: '#fff' }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="mt-6 p-4 bg-gray-800 shadow-lg rounded-lg">
              <Typography variant="h6" className="mb-2 text-white">Cargo Weight Trends</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={weightTrends}>
                  <XAxis dataKey="date" tick={{ fill: '#fff' }} />
                  <YAxis tick={{ fill: '#fff' }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="weight" stroke="#ff7300" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Home;
