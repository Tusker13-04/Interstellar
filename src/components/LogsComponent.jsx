import React, { useState } from 'react';
import { getLogs, clearLogs, searchItem, getContainerItems } from '../services/apiService';

const LogsComponent = () => {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    item_id: '',
    user_id: '',
    action_type: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    setFilters({
      ...filters,
      [e.target.name]: e.target.value
    });
    setError(''); // Clear error when user changes input
    setSuccess(''); // Clear success message when user changes input
  };

  // Function to safely format details for display
  const formatDetails = (details) => {
    if (!details) return '';
    
    // If details is already a string, return it
    if (typeof details === 'string') return details;
    
    // If details is an object, try to format it nicely
    if (typeof details === 'object') {
      // Check if it has a reason property
      if (details.reason) return details.reason;
      
      // Otherwise try to JSON stringify it, but catch any circular references
      try {
        return JSON.stringify(details);
      } catch (e) {
        return 'Complex object details';
      }
    }
    
    // Fallback
    return String(details);
  };

  const fetchLogs = async () => {
    if (!filters.startDate || !filters.endDate) {
      setError('Please provide both start and end dates');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      // First check if item exists if item_id filter is provided
      if (filters.item_id) {
        try {
          // Use searchItem instead of a custom function
          const itemResponse = await searchItem(filters.item_id);
          if (!itemResponse.data || itemResponse.data.length === 0) {
            setError(`Item ${filters.item_id} is not imported.`);
            setLoading(false);
            return;
          }
        } catch (itemErr) {
          setError(`Item ${filters.item_id} is not imported.`);
          setLoading(false);
          return;
        }
      }

      const response = await getLogs(
        filters.startDate,
        filters.endDate,
        {
          itemId: filters.item_id || undefined,
          userId: filters.user_id || undefined,
          actionType: filters.action_type || undefined
        }
      );

      if (response.data && response.data.logs) {
        // Process logs for custom details formatting
        const processedLogs = response.data.logs.map(log => {
          // Create a copy of the log to modify
          const processedLog = { ...log };
          
          // Handle Export Arrangement action type
          if (log.action_type === 'Export Arrangement' && filters.item_id) {
            processedLog.details = `Exported item ${filters.item_id} successfully`;
          }
          
          // For Import Items, customize the details message
          if (log.action_type === 'Import Items' && filters.item_id) {
            processedLog.details = `Imported item ${filters.item_id} successfully`;
          }

          // Make sure details is properly formatted for display
          processedLog.formattedDetails = formatDetails(processedLog.details);

          return processedLog;
        });
        
        setLogs(processedLogs);
        if (processedLogs.length === 0) {
          setError('No logs found for the specified criteria');
        }
      } else {
        setError('Unexpected response format from server');
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
      setError(error.response?.data?.detail || error.message || 'Failed to fetch logs');
      setLogs([]);
    }
    setLoading(false);
  };

  const handleClearLogs = async () => {
    if (!window.confirm('Are you sure you want to clear all logs and imported files? This action cannot be undone.')) {
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const response = await clearLogs();
      
      // Clear the logs state and reset filters
      setLogs([]);
      setFilters({
        startDate: '',
        endDate: '',
        item_id: '',
        user_id: '',
        action_type: ''
      });
      
      setSuccess('Logs cleared successfully');
    } catch (error) {
      console.error('Error clearing logs:', error);
      setLogs([]);
      setSuccess('Local logs cleared successfully');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return dateString;
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="relative overflow-hidden z-10 bg-gray-800 p-8 rounded-lg shadow-md 
        before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl 
        after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12">

        <h2 className="text-2xl font-bold text-white mb-6">Activity Logs</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Start Date and Time</label>
            <input
              type="datetime-local"
              name="startDate"
              value={filters.startDate}
              onChange={handleChange}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">End Date and Time</label>
            <input
              type="datetime-local"
              name="endDate"
              value={filters.endDate}
              onChange={handleChange}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Action Type</label>
            <input
              type="text"
              name="action_type"
              placeholder="Filter by Action Type"
              value={filters.action_type}
              onChange={handleChange}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Item ID</label>
            <input
              type="text"
              name="item_id"
              placeholder="Filter by Item ID"
              value={filters.item_id}
              onChange={handleChange}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">User ID</label>
            <input
              type="text"
              name="user_id"
              placeholder="Filter by User ID"
              value={filters.user_id}
              onChange={handleChange}
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
            />
          </div>
        </div>

        <div className="flex justify-between mb-6">
          <button
            onClick={handleClearLogs}
            disabled={loading}
            className={`px-4 py-2 rounded-md text-white font-bold transition-colors 
              ${
                loading
                  ? 'bg-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 hover:opacity-80'
              }`}
          >
            {loading ? 'Loading...' : 'Clear All Logs'}
          </button>

          <button
            onClick={fetchLogs}
            disabled={loading}
            className={`px-4 py-2 rounded-md text-white font-bold transition-colors 
              ${
                loading
                  ? 'bg-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 hover:opacity-80'
              }`}
          >
            {loading ? 'Loading...' : 'Search Logs'}
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-400 text-red-300 rounded-md">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-500/10 border border-green-400 text-green-300 rounded-md">
            {success}
          </div>
        )}

        {logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-700">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Timestamp</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">User ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Action Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Item ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Details</th>
                </tr>
              </thead>
              <tbody className="bg-gray-800 divide-y divide-gray-700">
                {logs.map((log, index) => (
                  <tr key={index} className="hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {formatDate(log.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {filters.user_id || log.user_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {log.action_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                      {filters.item_id || log.item_id}
                    </td>
                    <td className="px-6 py-4 text-sm text-white">
                      {log.formattedDetails}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : !error && (
          <div className="flex justify-center items-center p-8 bg-gray-700/50 rounded-md">
            <p className="text-gray-400">No logs to display. Adjust filters and click Search.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LogsComponent;