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
        <div className="max-w-lg w-full bg-white shadow-md rounded-lg p-6">
          <h2 className="text-2xl font-semibold mb-4 text-center">Retrieve an Item</h2>
          <form onSubmit={handleRetrieve} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Item ID
              </label>
              <input 
                type="text" 
                name="itemId"
                value={formData.itemId} 
                onChange={handleInputChange} 
                placeholder="Enter Item ID" 
                required 
                className="w-full border p-2 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                User ID (Optional)
              </label>
              <input 
                type="text" 
                name="userId"
                value={formData.userId} 
                onChange={handleInputChange} 
                placeholder="Enter User ID" 
                className="w-full border p-2 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Timestamp (Optional)
              </label>
              <input 
                type="datetime-local" 
                name="timestamp"
                value={formData.timestamp} 
                onChange={handleInputChange} 
                className="w-full border p-2 rounded-md"
              />
            </div>

            <button 
              type="submit"
              className={`w-full py-2 text-white rounded-md ${
                loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'
              }`}
              disabled={loading || !formData.itemId}
            >
              {loading ? 'Retrieving Item...' : 'Retrieve Item'}
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
        </div>
      </div>
    </div>
  );
};

export default RetrieveItemComponent;
