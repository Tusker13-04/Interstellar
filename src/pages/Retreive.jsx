import { useState } from 'react';
import SideNavBar from "../components/dashboard/sideNavBar";
import { retrieveItem } from '../services/apiService';

const RetrieveItemComponent = () => {
  const [formData, setFormData] = useState({
    itemId: '',
    userId: '',
    timestamp: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRetrieve = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    if (!formData.itemId.trim()) {
      setMessage('Item ID is required');
      setLoading(false);
      return;
    }

    try {
      const requestData = {
        itemId: formData.itemId.trim(),
        timestamp: formData.timestamp || undefined
      };

      // Only add userId if it's not empty
      if (formData.userId.trim()) {
        requestData.userId = formData.userId.trim();
      }

      const response = await retrieveItem(requestData);
      
      console.log('Retrieve response:', response);
      
      if (response.success) {
        setMessage(`Item retrieved successfully!`);
        // Clear form after successful retrieval
        setFormData({
          itemId: '',
          userId: '',
          timestamp: ''
        });
      } else {
        setMessage('Failed to retrieve item. Please check if the item exists and try again.');
      }
    } catch (error) {
      console.error('Error retrieving item:', error);
      setMessage(error.message || 'Error occurred while retrieving item. Please try again.');
    }

    setLoading(false);
  };

  return (
    <div className="flex h-screen">
  <div className="hidden md:block md:w-64 bg-white shadow-lg fixed h-full">
    <SideNavBar />
  </div>

  <div className="flex-1 flex justify-center items-center p-8 ml-64">
    <div className="relative max-w-md w-full bg-gray-800 p-8 rounded-lg shadow-md overflow-hidden z-10 
        before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl 
        after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12"
    >
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Retrieve an Item</h2>

      <form onSubmit={handleRetrieve} className="space-y-4 text-white">
        <div>
          <label className="block text-sm font-medium mb-1">
            Item ID
          </label>
          <input
            type="text"
            name="itemId"
            value={formData.itemId}
            onChange={handleInputChange}
            placeholder="Enter Item ID"
            required
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            User ID (Optional)
          </label>
          <input
            type="text"
            name="userId"
            value={formData.userId}
            onChange={handleInputChange}
            placeholder="Enter User ID"
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            Timestamp (Optional)
          </label>
          <input
            type="datetime-local"
            name="timestamp"
            value={formData.timestamp}
            onChange={handleInputChange}
            className="w-full p-2 bg-gray-700 border border-gray-600 rounded-md"
          />
        </div>

        <button
          type="submit"
          className={`w-full py-2 font-bold rounded-md text-white ${
            loading
              ? 'bg-gray-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 hover:opacity-80'
          }`}
          disabled={loading || !formData.itemId}
        >
          {loading ? 'Retrieving Item...' : 'Retrieve Item'}
        </button>
      </form>

      {message && (
        <div className={`mt-4 p-3 rounded-md text-sm font-medium ${
          message.includes('successfully')
            ? 'bg-green-700 text-green-100'
            : 'bg-red-700 text-red-100'
        }`}>
          {message}
        </div>
      )}
    </div>
  </div>
</div>

  );
};

export default RetrieveItemComponent;
