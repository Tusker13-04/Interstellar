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

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString();
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
        requestData.toTimestamp = formData.toTimestamp;
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
    <div className="flex-1 p-6 bg-white shadow-lg rounded-lg max-w-4xl mx-auto">
      <h2 className="text-2xl font-semibold mb-4">Time Simulation</h2>
      
      <form onSubmit={handleSimulate} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Number of Days
            </label>
            <input
              type="number"
              name="numOfDays"
              value={formData.numOfDays}
              onChange={handleInputChange}
              placeholder="Enter number of days"
              className="w-full border p-2 rounded-md"
              min="1"
              disabled={formData.toTimestamp !== ''}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target Date/Time
            </label>
            <input
              type="datetime-local"
              name="toTimestamp"
              value={formData.toTimestamp}
              onChange={handleInputChange}
              className="w-full border p-2 rounded-md"
              disabled={formData.numOfDays !== ''}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Item ID
            </label>
            <input
              type="number"
              name="itemId"
              value={formData.itemId}
              onChange={handleInputChange}
              placeholder="Enter Item ID"
              className="w-full border p-2 rounded-md"
              disabled={formData.itemName !== ''}
              min="1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Item Name
            </label>
            <input
              type="text"
              name="itemName"
              value={formData.itemName}
              onChange={handleInputChange}
              placeholder="Enter Item Name"
              className="w-full border p-2 rounded-md"
              disabled={formData.itemId !== ''}
            />
          </div>
        </div>

        <p className="text-sm text-gray-500 italic">
          Note: Provide either Item ID or Item Name, not both
        </p>

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2 text-white rounded-md ${
            loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-500 hover:bg-green-600'
          }`}
        >
          {loading ? 'Running Simulation...' : 'Run Simulation'}
        </button>
      </form>

      {message && (
        <div className={`mt-4 p-3 rounded-md ${
          message.includes('successfully')
            ? 'bg-green-50 border border-green-200 text-green-600'
            : 'bg-red-50 border border-red-200 text-red-600'
        }`}>
          {message}
        </div>
      )}

      {simulationResults && simulationResults.success && (
        <div className="mt-6 space-y-4 text-sm">
          <div className="bg-blue-50 p-4 rounded-md">
            <p className="text-blue-700 font-medium">
              Final Simulation Date: {formatDate(simulationResults.newDate)}
            </p>
          </div>

          {getSummarizedItemData().length > 0 && (
            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="font-medium mb-2">Items Status After Simulation:</h4>
              <ul className="list-disc pl-5 space-y-2">
                {getSummarizedItemData().map((item, index) => (
                  <li key={`used-${index}`}>
                    <span className="font-medium">
                      {item.name}
                    </span>
                    <br />
                    <span className="text-gray-600">
                      {item.count > 1 
                        ? `${item.count} items with average of ${Math.round(item.totalRemainingUses / item.count)} uses left (range: ${item.minRemainingUses}-${item.maxRemainingUses})`
                        : `Remaining Uses: ${item.totalRemainingUses}`
                      }
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {getSummarizedExpiredItems().length > 0 && (
            <div className="bg-yellow-50 p-4 rounded-md">
              <h4 className="font-medium mb-2 text-yellow-800">Expired Items:</h4>
              <ul className="list-disc pl-5 space-y-2">
                {getSummarizedExpiredItems().map((item, index) => (
                  <li key={`expired-${index}`} className="text-yellow-800">
                    {item.name} {item.count > 1 ? `(${item.count} items)` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {getSummarizedDepletedItems().length > 0 && (
            <div className="bg-red-50 p-4 rounded-md">
              <h4 className="font-medium mb-2 text-red-800">Depleted Items:</h4>
              <ul className="list-disc pl-5 space-y-2">
                {getSummarizedDepletedItems().map((item, index) => (
                  <li key={`depleted-${index}`} className="text-red-800">
                    {item.name} {item.count > 1 ? `(${item.count} items)` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {getSummarizedItemData().length === 0 &&
           getSummarizedExpiredItems().length === 0 &&
           getSummarizedDepletedItems().length === 0 && (
            <div className="bg-gray-50 p-4 rounded-md">
              <p className="text-gray-600">No changes to report for this simulation.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SimulationComponent;