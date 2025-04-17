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
  <div className="flex-1 max-w-4xl mx-auto relative overflow-hidden z-10 bg-gray-800 p-8 rounded-lg shadow-md before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12">
    <h2 className="text-2xl font-bold text-white mb-6">Waste Management</h2>

    <button
      onClick={fetchWasteItems}
      className="w-full py-2 bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white font-bold rounded-md hover:opacity-80"
    >
      Identify Waste Items
    </button>

    {loading && <p className="mt-2 text-gray-400">Loading...</p>}

    {message && (
      <div
        className={`mt-4 p-3 rounded-md text-sm ${
          message.includes("successfully")
            ? "bg-green-600 text-white"
            : "bg-red-600 text-white"
        }`}
      >
        {message}
      </div>
    )}

    {wasteItems.length > 0 && (
      <div className="mt-4 p-4 bg-gray-700 rounded-lg text-white">
        <h3 className="text-lg font-medium mb-2">Waste Items:</h3>
        <ul className="space-y-2 text-sm">
          {wasteItems.map((item) => (
            <li key={item.itemId} className="border-b border-gray-600 pb-2">
              <strong>{item.name}</strong> - {item.reason}
            </li>
          ))}
        </ul>
      </div>
    )}

    <form onSubmit={handleReturnPlan} className="mt-6 space-y-4">
      <h3 className="text-lg font-medium text-white">Request Return Plan</h3>

      <input
        type="text"
        placeholder="Undocking Container ID"
        name="undockingContainerId"
        value={undockingInfo.undockingContainerId}
        onChange={(e) =>
          setUndockingInfo({
            ...undockingInfo,
            undockingContainerId: e.target.value,
          })
        }
        required
        className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
      />

      <input
        type="date"
        name="undockingDate"
        value={undockingInfo.undockingDate}
        onChange={(e) =>
          setUndockingInfo({
            ...undockingInfo,
            undockingDate: e.target.value,
          })
        }
        required
        className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
      />

      <input
        type="number"
        placeholder="Max Weight (kg)"
        name="maxWeight"
        value={undockingInfo.maxWeight}
        onChange={(e) =>
          setUndockingInfo({
            ...undockingInfo,
            maxWeight: e.target.value,
          })
        }
        required
        className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
      />

      <button
        type="submit"
        className="w-full py-2 bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white font-bold rounded-md hover:opacity-80"
      >
        Get Return Plan
      </button>
    </form>

    {returnPlan && (
      <div className="mt-6 p-4 bg-gray-700 rounded-lg text-white space-y-6">
        <div>
          <h3 className="text-lg font-medium mb-2">Return Manifest</h3>
          <p className="text-sm">Container ID: {returnPlan.return_manifest.undocking_container_id}</p>
          <p className="text-sm">Undocking Date: {new Date(returnPlan.return_manifest.undocking_date).toLocaleDateString()}</p>
          <p className="text-sm">Total Weight: {returnPlan.return_manifest.total_weight} kg</p>
          <p className="text-sm">Total Volume: {returnPlan.return_manifest.total_volume} m³</p>
        </div>

        {returnPlan.return_manifest.return_items.length > 0 && (
          <div>
            <h4 className="text-md font-medium mb-2">Items to Return:</h4>
            <ul className="space-y-1 text-sm">
              {returnPlan.return_manifest.return_items.map((item, index) => (
                <li key={index}>
                  • {item.name} (ID: {item.itemId}) - {item.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {returnPlan.return_plan.length > 0 && (
          <div>
            <h4 className="text-md font-medium mb-2">Return Steps:</h4>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {returnPlan.return_plan.map((step, index) => (
                <li key={index}>
                  Move {step.item_name} from {step.from_container} to {step.to_container}
                </li>
              ))}
            </ol>
          </div>
        )}

        {returnPlan.retrieval_steps.length > 0 && (
          <div>
            <h4 className="text-md font-medium mb-2">Retrieval Steps:</h4>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {returnPlan.retrieval_steps.map((step, index) => (
                <li key={index}>
                  {step.action.charAt(0).toUpperCase() + step.action.slice(1)} {step.item_name}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    )}

    <button
      onClick={handleCompleteUndocking}
      disabled={!undockingInfo.undockingContainerId}
      className={`mt-6 w-full py-2 text-white font-bold rounded-md ${
        !undockingInfo.undockingContainerId
          ? "bg-gray-600 cursor-not-allowed"
          : "bg-gradient-to-r from-red-600 via-red-500 to-pink-500 hover:opacity-80"
      }`}
    >
      Complete Undocking
    </button>
  </div>
</div>

  );
};

export default WasteManagement;
