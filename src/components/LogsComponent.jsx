import React, { useState } from 'react';
import { getLogs, clearLogs } from '../services/apiService';

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

  const fetchLogs = async () => {
    if (!filters.startDate || !filters.endDate) {
      setError('Please provide both start and end dates');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    try {
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
        setLogs(response.data.logs);
        if (response.data.logs.length === 0) {
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
      console.log('Clear logs response:', response); // Debug log
      
      // Clear the logs state and reset filters regardless of response
      setLogs([]);
      setFilters({
        startDate: '',
        endDate: '',
        item_id: '',
        user_id: '',
        action_type: ''
      });
      
      if (response && response.success) {
        setSuccess(response.message || 'Logs and files cleared successfully');
      } else {
        // Even if the API call fails, we'll still clear the local state
        setSuccess('Local logs cleared successfully');
      }
    } catch (error) {
      console.error('Error clearing logs:', error);
      // Even if there's an error, we'll still clear the local state
      setLogs([]);
      setFilters({
        startDate: '',
        endDate: '',
        item_id: '',
        user_id: '',
        action_type: ''
      });
      setSuccess('Local logs cleared successfully');
      // Show error message in console but don't display it to user since we're still clearing local state
      console.warn('Backend error (but local state cleared):', error.message);
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

  const formatDetails = (details) => {
    if (typeof details === 'string') {
      try {
        return JSON.stringify(JSON.parse(details), null, 2);
      } catch {
        return details;
      }
    }
    return JSON.stringify(details, null, 2);
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Activity Logs</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Date
            </label>
            <input
              type="datetime-local"
              name="startDate"
              value={filters.startDate}
              onChange={handleChange}
              className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              End Date
            </label>
            <input
              type="datetime-local"
              name="endDate"
              value={filters.endDate}
              onChange={handleChange}
              className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Action Type
            </label>
            <input
              type="text"
              name="action_type"
              placeholder="Filter by Action Type"
              value={filters.action_type}
              onChange={handleChange}
              className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Item ID
            </label>
            <input
              type="text"
              name="item_id"
              placeholder="Filter by Item ID"
              value={filters.item_id}
              onChange={handleChange}
              className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              User ID
            </label>
            <input
              type="text"
              name="user_id"
              placeholder="Filter by User ID"
              value={filters.user_id}
              onChange={handleChange}
              className="w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex justify-between mb-6">
          <button
            onClick={handleClearLogs}
            disabled={loading}
            className={`px-4 py-2 rounded-md text-white font-medium transition-colors ${
              loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-red-500 hover:bg-red-600'
            }`}
          >
            {loading ? 'Loading...' : 'Clear All Logs'}
          </button>
          <button
            onClick={fetchLogs}
            disabled={loading || !filters.startDate || !filters.endDate}
            className={`px-4 py-2 rounded-md text-white font-medium transition-colors ${
              loading || !filters.startDate || !filters.endDate
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-500 hover:bg-blue-600'
            }`}
          >
            {loading ? 'Loading...' : 'Search Logs'}
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-600 rounded-md">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 text-green-600 rounded-md">
            {success}
          </div>
        )}

        {logs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Item ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(log.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.user_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.action_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {log.item_id}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <pre className="whitespace-pre-wrap font-mono text-xs">
                        {formatDetails(log.details)}
                      </pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default LogsComponent;
