import { useState } from 'react';
import SideNavBar from "../components/dashboard/sideNavBar";
import { placeItem } from '../services/apiService';

const PlaceItemComponent = () => {
  const [formData, setFormData] = useState({
    itemId: '',
    userId: 'user123',
    containerId: '',
    position: {
      startCoordinates: { width: '', depth: '', height: '' },
      endCoordinates: { width: '', depth: '', height: '' }
    }
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    const keys = name.split('.');

    if (keys.length === 1) {
      setFormData((prev) => ({ ...prev, [name]: value }));
    } else {
      setFormData((prev) => ({
        ...prev,
        position: {
          ...prev.position,
          [keys[0]]: {
            ...prev.position[keys[0]],
            [keys[1]]: value
          }
        }
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await placeItem({
        ...formData,
        timestamp: new Date().toISOString(),
        position: {
          startCoordinates: {
            width: parseFloat(formData.position.startCoordinates.width),
            depth: parseFloat(formData.position.startCoordinates.depth),
            height: parseFloat(formData.position.startCoordinates.height)
          },
          endCoordinates: {
            width: parseFloat(formData.position.endCoordinates.width),
            depth: parseFloat(formData.position.endCoordinates.depth),
            height: parseFloat(formData.position.endCoordinates.height)
          }
        }
      });

      if (response.data.success) {
        setMessage(' Item placed successfully!');
      } else {
        setMessage(' Failed to place item.');
      }
    } catch (error) {
      console.error('Error placing item:', error);
      setMessage(' Error occurred while placing item.');
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
          <h2 className="text-2xl font-semibold mb-4 text-center">Place an Item</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <input 
              type="text" 
              name="itemId" 
              value={formData.itemId} 
              onChange={handleChange} 
              placeholder="Item ID"
              required 
              className="w-full border p-2 rounded-md"
            />

            <input 
              type="text" 
              name="containerId" 
              value={formData.containerId} 
              onChange={handleChange} 
              placeholder="Container ID"
              required 
              className="w-full border p-2 rounded-md"
            />

            <div className="bg-gray-100 p-4 rounded-md">
              <h3 className="text-lg font-medium mb-2">Start Coordinates</h3>
              <div className="flex space-x-2">
                <input type="number" name="startCoordinates.width" placeholder="Width" value={formData.position.startCoordinates.width} onChange={handleChange} className="border p-2 w-1/3 rounded-md" required />
                <input type="number" name="startCoordinates.depth" placeholder="Depth" value={formData.position.startCoordinates.depth} onChange={handleChange} className="border p-2 w-1/3 rounded-md" required />
                <input type="number" name="startCoordinates.height" placeholder="Height" value={formData.position.startCoordinates.height} onChange={handleChange} className="border p-2 w-1/3 rounded-md" required />
              </div>
            </div>
            <div className="bg-gray-100 p-4 rounded-md">
              <h3 className="text-lg font-medium mb-2">End Coordinates</h3>
              <div className="flex space-x-2">
                <input type="number" name="endCoordinates.width" placeholder="Width" value={formData.position.endCoordinates.width} onChange={handleChange} className="border p-2 w-1/3 rounded-md" required />
                <input type="number" name="endCoordinates.depth" placeholder="Depth" value={formData.position.endCoordinates.depth} onChange={handleChange} className="border p-2 w-1/3 rounded-md" required />
                <input type="number" name="endCoordinates.height" placeholder="Height" value={formData.position.endCoordinates.height} onChange={handleChange} className="border p-2 w-1/3 rounded-md" required />
              </div>
            </div>

            <button 
              type="submit"
              className={`w-full py-2 text-white rounded-md ${loading ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'}`}
              disabled={loading}
            >
              {loading ? 'Placing Item...' : 'Place Item'}
            </button>
          </form>

          {message && (
            <p className={`mt-4 text-center font-medium ${message.includes('✅') ? 'text-green-600' : 'text-red-600'}`}>
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlaceItemComponent;
