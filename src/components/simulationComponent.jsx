import { useState } from "react";
import { simulateDays } from "../services/apiService";

const SimulationComponent = () => {
  const [formData, setFormData] = useState({
    numOfDays: '',
    toTimestamp: '',
    itemId: '',
    itemName: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [simulationResults, setSimulationResults] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
      // Handle Item ID and Item Name mutual exclusivity
      ...(name === 'itemId' && value !== '' ? { itemName: '' } : {}),
      ...(name === 'itemName' && value !== '' ? { itemId: '' } : {}),
      // Handle Number of Days and Target Date/Time mutual exclusivity
      ...(name === 'numOfDays' && value !== '' ? { toTimestamp: '' } : {}),
      ...(name === 'toTimestamp' && value !== '' ? { numOfDays: '' } : {})
    }));
  };

  // Format the date for display purposes
  const formatDate = (isoString) => {
    try {
      return new Date(isoString).toLocaleString();
    } catch (error) {
      console.error("Error formatting date:", error);
      return isoString; // Fallback to original string
    }
  };

  // Format the date for API request (to UTC format with Z)
  const formatDateForApi = (dateString) => {
    if (!dateString) return '';
    try {
      // Create a date object and convert to UTC ISO string
      const date = new Date(dateString);
      return date.toISOString().split('.')[0] + 'Z'; // Remove milliseconds and add Z
    } catch (error) {
      console.error("Error formatting date for API:", error);
      return dateString; // Return original string if conversion fails
    }
  };

  const handleSimulate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setSimulationResults(null);

    try {
      // Check if either days or target date is provided
      if (!formData.numOfDays && !formData.toTimestamp) {
        setMessage('Either Number of Days or Target Date/Time is required');
        setLoading(false);
        return;
      }

      // Check if either item ID or name is provided
      if (!formData.itemId && !formData.itemName) {
        setMessage('Either Item ID or Item Name is required');
        setLoading(false);
        return;
      }

      // Format the request data properly
      const requestData = {
        itemsToBeUsedPerDay: []
      };

      // Create item usage object based on which field was provided
      const itemUsage = {};
      
      if (formData.itemId) {
        itemUsage.itemId = formData.itemId.toString();
      } else if (formData.itemName) {
        itemUsage.name = formData.itemName.trim();
      }
      
      requestData.itemsToBeUsedPerDay.push(itemUsage);

      // Add either numOfDays or toTimestamp, but not both
      if (formData.numOfDays) {
        requestData.numOfDays = parseInt(formData.numOfDays);
      } else if (formData.toTimestamp) {
        // Format timestamp in UTC Z format for API
        requestData.toTimestamp = formatDateForApi(formData.toTimestamp);
      }

      console.log('Sending simulation request:', requestData);
      const response = await simulateDays(requestData);
      console.log('Simulation response:', response);

      if (response.success) {
        setMessage('Simulation completed successfully!');
        setSimulationResults(response);
        setFormData({
          numOfDays: '',
          toTimestamp: '',
          itemId: '',
          itemName: ''
        });
      } else {
        setMessage(response.error || 'Simulation failed');
      }
    } catch (error) {
      console.error('Simulation error:', error);
      setMessage(error.message || 'Failed to simulate time');
    } finally {
      setLoading(false);
    }
  };

  // Function to get summarized item data
  const getSummarizedItemData = () => {
    if (!simulationResults || !simulationResults.changes) return [];
    
    // Create a map to aggregate items by name
    const itemsMap = new Map();
    
    // Filter out depleted items
    const nonDepletedItems = simulationResults.changes.itemsUsed.filter(
      item => !simulationResults.changes.itemsDepletedToday.some(
        depleted => depleted.itemId === item.itemId
      )
    );
    
    // Count unique items by name
    nonDepletedItems.forEach(item => {
      if (!itemsMap.has(item.name)) {
        itemsMap.set(item.name, {
          name: item.name,
          count: 1,
          totalRemainingUses: item.remainingUses,
          minRemainingUses: item.remainingUses,
          maxRemainingUses: item.remainingUses,
          // Only store sample item ID if needed for reference
          sampleItemId: item.itemId
        });
      } else {
        const existing = itemsMap.get(item.name);
        existing.count++;
        existing.totalRemainingUses += item.remainingUses;
        existing.minRemainingUses = Math.min(existing.minRemainingUses, item.remainingUses);
        existing.maxRemainingUses = Math.max(existing.maxRemainingUses, item.remainingUses);
      }
    });
    
    return Array.from(itemsMap.values());
  };

  // Function to get summarized expired items
  const getSummarizedExpiredItems = () => {
    if (!simulationResults || !simulationResults.changes) return [];
    
    const itemsMap = new Map();
    simulationResults.changes.itemsExpired.forEach(item => {
      if (!itemsMap.has(item.name)) {
        itemsMap.set(item.name, {
          name: item.name,
          count: 1,
          sampleItemId: item.itemId
        });
      } else {
        itemsMap.get(item.name).count++;
      }
    });
    
    return Array.from(itemsMap.values());
  };

  // Function to get summarized depleted items
  const getSummarizedDepletedItems = () => {
    if (!simulationResults || !simulationResults.changes) return [];
    
    const itemsMap = new Map();
    simulationResults.changes.itemsDepletedToday.forEach(item => {
      if (!itemsMap.has(item.name)) {
        itemsMap.set(item.name, {
          name: item.name,
          count: 1,
          sampleItemId: item.itemId
        });
      } else {
        itemsMap.get(item.name).count++;
      }
    });
    
    return Array.from(itemsMap.values());
  };

  return (
    <div className="max-w-4xl mx-auto relative overflow-hidden z-10 bg-gray-800 p-8 rounded-lg shadow-md before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12">
  <h2 className="text-2xl font-bold text-white mb-6">Time Simulation</h2>

  <form onSubmit={handleSimulate} className="space-y-6">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Number of Days
        </label>
        <input
          type="number"
          name="numOfDays"
          value={formData.numOfDays}
          onChange={handleInputChange}
          placeholder="Enter number of days"
          className="mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white"
          min="1"
          disabled={formData.toTimestamp !== ''}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Target Date/Time
        </label>
        <input
          type="datetime-local"
          name="toTimestamp"
          value={formData.toTimestamp}
          onChange={handleInputChange}
          className="mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white"
          disabled={formData.numOfDays !== ''}
        />
      </div>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Item ID
        </label>
        <input
          type="number"
          name="itemId"
          value={formData.itemId}
          onChange={handleInputChange}
          placeholder="Enter Item ID"
          className="mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white"
          disabled={formData.itemName !== ''}
          min="1"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Item Name
        </label>
        <input
          type="text"
          name="itemName"
          value={formData.itemName}
          onChange={handleInputChange}
          placeholder="Enter Item Name"
          className="mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white"
          disabled={formData.itemId !== ''}
        />
      </div>
    </div>

    <p className="text-sm text-gray-400 italic">
      Note: Provide either Item ID or Item Name, not both
    </p>

    <button
      type="submit"
      disabled={loading}
      className={`w-full py-2 font-bold rounded-md text-white ${
        loading
          ? 'bg-gray-500 cursor-not-allowed'
          : 'bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 hover:opacity-80'
      }`}
    >
      {loading ? 'Running Simulation...' : 'Run Simulation'}
    </button>
  </form>

  {message && (
    <div
      className={`mt-6 p-3 rounded-md font-medium ${
        message.includes('successfully')
          ? 'bg-green-100 border border-green-300 text-green-800'
          : 'bg-red-100 border border-red-300 text-red-800'
      }`}
    >
      {message}
    </div>
  )}

  {simulationResults?.success && (
    <div className="mt-8 space-y-6 text-sm text-white">
      <div className="bg-blue-900/30 p-4 rounded-md border border-blue-600">
        <p className="text-blue-300 font-semibold">
          Final Simulation Date: {formatDate(simulationResults.newDate)}
        </p>
      </div>

      {getSummarizedItemData().length > 0 && (
        <div className="bg-gray-700 p-4 rounded-md border border-gray-600">
          <h4 className="font-semibold mb-2">Items Status After Simulation:</h4>
          <ul className="list-disc pl-5 space-y-2 text-gray-300">
            {getSummarizedItemData().map((item, index) => (
              <li key={`used-${index}`}>
                <span className="font-semibold">{item.name}</span>
                <br />
                <span className="text-gray-400">
                  {item.count > 1
                    ? `${item.count} items with average of ${Math.round(
                        item.totalRemainingUses / item.count
                      )} uses left (range: ${item.minRemainingUses}-${item.maxRemainingUses})`
                    : `Remaining Uses: ${item.totalRemainingUses}`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {getSummarizedExpiredItems().length > 0 && (
        <div className="bg-yellow-900/20 p-4 rounded-md border border-yellow-600">
          <h4 className="font-semibold mb-2 text-yellow-300">Expired Items:</h4>
          <ul className="list-disc pl-5 space-y-2 text-yellow-200">
            {getSummarizedExpiredItems().map((item, index) => (
              <li key={`expired-${index}`}>
                {item.name} {item.count > 1 ? `(${item.count} items)` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {getSummarizedDepletedItems().length > 0 && (
        <div className="bg-red-900/20 p-4 rounded-md border border-red-600">
          <h4 className="font-semibold mb-2 text-red-300">Depleted Items:</h4>
          <ul className="list-disc pl-5 space-y-2 text-red-200">
            {getSummarizedDepletedItems().map((item, index) => (
              <li key={`depleted-${index}`}>
                {item.name} {item.count > 1 ? `(${item.count} items)` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {getSummarizedItemData().length === 0 &&
        getSummarizedExpiredItems().length === 0 &&
        getSummarizedDepletedItems().length === 0 && (
          <div className="bg-gray-700 p-4 rounded-md border border-gray-600">
            <p className="text-gray-300">
              No changes to report for this simulation.
            </p>
          </div>
        )}
    </div>
  )}
</div>

  );
};

export default SimulationComponent;