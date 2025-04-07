import { useState } from 'react';
import { identifyWaste, returnWastePlan, completeUndocking } from '../services/apiService';

const WasteManagement = () => {
  const [wasteItems, setWasteItems] = useState([]);
  const [returnPlan, setReturnPlan] = useState(null);
  const [undockingInfo, setUndockingInfo] = useState({
    undockingContainerId: '',
    undockingDate: '',
    maxWeight: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const fetchWasteItems = async () => {
    setLoading(true);
    setMessage('');
    try {
      console.log('Fetching waste items...');
      const response = await identifyWaste();
      console.log('Received waste items response:', response);
      if (response.data && response.data.wasteItems) {
        console.log('Setting waste items:', response.data.wasteItems);
        setWasteItems(response.data.wasteItems);
      } else {
        console.log('No waste items found in response');
        setWasteItems([]);
      }
    } catch (error) {
      console.error('Error fetching waste items:', error);
      setMessage('Error fetching waste items.');
    }
    setLoading(false);
  };

  const handleReturnPlan = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      const response = await returnWastePlan({
        ...undockingInfo,
        undockingDate: new Date(undockingInfo.undockingDate).toISOString(),
        maxWeight: parseFloat(undockingInfo.maxWeight),
      });
      setReturnPlan(response.data);
    } catch (error) {
      setMessage(' Error requesting return plan.');
      console.error(error);
    }
    setLoading(false);
  };

  const handleCompleteUndocking = async () => {
    setMessage('');
    try {
      const response = await completeUndocking({
        undockingContainerId: undockingInfo.undockingContainerId,
        timestamp: new Date().toISOString(),
      });
      console.log('Complete undocking response:', response.data);
      
      setWasteItems([]);
      setMessage(`Undocking completed successfully!`);
      setReturnPlan(null);
      setUndockingInfo({
        undockingContainerId: '',
        undockingDate: '',
        maxWeight: '',
      });
    } catch (error) {
      console.error('Error completing undocking:', error);
      setMessage(`Error completing undocking: ${error.response?.data?.detail || error.message}`);
    }
  };

  return (
    <div className="flex">
      <div className="flex-1 p-6 bg-white shadow-lg rounded-lg max-w-4xl mx-auto">
        <h2 className="text-2xl font-semibold mb-4"> Waste Management</h2>
        
        <button onClick={fetchWasteItems} className="w-full py-2 bg-blue-500 text-white rounded-md hover:bg-blue-700">
          Identify Waste Items
        </button>
        {loading && <p className="mt-2 text-gray-500">Loading...</p>}
        {message && (
          <div className={`mt-4 p-3 rounded-md ${
            message.includes('successfully') 
              ? 'bg-green-50 border border-green-200 text-green-600' 
              : 'bg-red-50 border border-red-200 text-red-600'
          }`}>
            {message}
          </div>
        )}

        {wasteItems.length > 0 && (
          <div className="mt-4 p-4 bg-gray-100 rounded-lg">
            <h3 className="text-lg font-medium">Waste Items:</h3>
            <ul>
              {wasteItems.map((item) => (
                <li key={item.itemId} className="p-2 border-b">
                  <strong>{item.name}</strong> - {item.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        <form onSubmit={handleReturnPlan} className="mt-6 space-y-4">
          <h3 className="text-lg font-medium">Request Return Plan</h3>
          <input type="text" placeholder="Undocking Container ID" name="undockingContainerId" value={undockingInfo.undockingContainerId} onChange={(e) => setUndockingInfo({ ...undockingInfo, undockingContainerId: e.target.value })} required className="w-full border p-2 rounded-md" />
          <input type="date" name="undockingDate" value={undockingInfo.undockingDate} onChange={(e) => setUndockingInfo({ ...undockingInfo, undockingDate: e.target.value })} required className="w-full border p-2 rounded-md" />
          <input type="number" placeholder="Max Weight (kg)" name="maxWeight" value={undockingInfo.maxWeight} onChange={(e) => setUndockingInfo({ ...undockingInfo, maxWeight: e.target.value })} required className="w-full border p-2 rounded-md" />
          <button type="submit" className="w-full py-2 bg-green-500 text-white rounded-md hover:bg-green-700">Get Return Plan</button>
        </form>
        
        {returnPlan && (
          <div className="mt-4 p-4 bg-gray-100 rounded-lg">
            <h3 className="text-lg font-medium mb-3">Return Plan:</h3>
            <div className="space-y-4">
              <div className="bg-white p-3 rounded-md shadow-sm">
                <h4 className="font-medium text-gray-700">Return Manifest</h4>
                <p className="text-sm text-gray-600">Container ID: {returnPlan.return_manifest.undocking_container_id}</p>
                <p className="text-sm text-gray-600">Undocking Date: {new Date(returnPlan.return_manifest.undocking_date).toLocaleDateString()}</p>
                <p className="text-sm text-gray-600">Total Weight: {returnPlan.return_manifest.total_weight} kg</p>
                <p className="text-sm text-gray-600">Total Volume: {returnPlan.return_manifest.total_volume} m³</p>
              </div>

              {returnPlan.return_manifest.return_items.length > 0 && (
                <div className="bg-white p-3 rounded-md shadow-sm">
                  <h4 className="font-medium text-gray-700 mb-2">Items to Return:</h4>
                  <ul className="space-y-2">
                    {returnPlan.return_manifest.return_items.map((item, index) => (
                      <li key={index} className="text-sm text-gray-600">
                        • {item.name} (ID: {item.itemId}) - {item.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {returnPlan.return_plan.length > 0 && (
                <div className="bg-white p-3 rounded-md shadow-sm">
                  <h4 className="font-medium text-gray-700 mb-2">Return Steps:</h4>
                  <ol className="list-decimal list-inside space-y-2">
                    {returnPlan.return_plan.map((step, index) => (
                      <li key={index} className="text-sm text-gray-600">
                        Move {step.item_name} from {step.from_container} to {step.to_container}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {returnPlan.retrieval_steps.length > 0 && (
                <div className="bg-white p-3 rounded-md shadow-sm">
                  <h4 className="font-medium text-gray-700 mb-2">Retrieval Steps:</h4>
                  <ol className="list-decimal list-inside space-y-2">
                    {returnPlan.retrieval_steps.map((step, index) => (
                      <li key={index} className="text-sm text-gray-600">
                        {step.action.charAt(0).toUpperCase() + step.action.slice(1)} {step.item_name}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          </div>
        )}
        
        <button 
          onClick={handleCompleteUndocking} 
          disabled={!undockingInfo.undockingContainerId}
          className={`mt-6 w-full py-2 text-white rounded-md ${
            !undockingInfo.undockingContainerId 
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-red-500 hover:bg-red-700'
          }`}
        >
          Complete Undocking
        </button>
      </div>
    </div>
  );
};

export default WasteManagement;
