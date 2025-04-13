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
    <div className="relative max-w-md w-full bg-gray-800 p-8 rounded-lg shadow-md overflow-hidden z-10 
        before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl 
        after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12"
    >
      <h2 className="text-2xl font-bold text-white mb-6 text-center">Place an Item</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          name="itemId"
          value={formData.itemId}
          onChange={handleChange}
          placeholder="Item ID"
          required
          className="w-full mt-1 p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
        />

        <input
          type="text"
          name="containerId"
          value={formData.containerId}
          onChange={handleChange}
          placeholder="Container ID"
          required
          className="w-full mt-1 p-2 bg-gray-700 border border-gray-600 rounded-md text-white"
        />

        <div className="bg-gray-700 p-4 rounded-md border border-gray-600">
          <h3 className="text-white text-lg font-medium mb-2">Start Coordinates</h3>
          <div className="flex space-x-2">
            <input
              type="number"
              name="startCoordinates.width"
              placeholder="Width"
              value={formData.position.startCoordinates.width}
              onChange={handleChange}
              className="w-1/3 p-2 bg-gray-800 border border-gray-600 rounded-md text-white"
              required
            />
            <input
              type="number"
              name="startCoordinates.depth"
              placeholder="Depth"
              value={formData.position.startCoordinates.depth}
              onChange={handleChange}
              className="w-1/3 p-2 bg-gray-800 border border-gray-600 rounded-md text-white"
              required
            />
            <input
              type="number"
              name="startCoordinates.height"
              placeholder="Height"
              value={formData.position.startCoordinates.height}
              onChange={handleChange}
              className="w-1/3 p-2 bg-gray-800 border border-gray-600 rounded-md text-white"
              required
            />
          </div>
        </div>

        <div className="bg-gray-700 p-4 rounded-md border border-gray-600">
          <h3 className="text-white text-lg font-medium mb-2">End Coordinates</h3>
          <div className="flex space-x-2">
            <input
              type="number"
              name="endCoordinates.width"
              placeholder="Width"
              value={formData.position.endCoordinates.width}
              onChange={handleChange}
              className="w-1/3 p-2 bg-gray-800 border border-gray-600 rounded-md text-white"
              required
            />
            <input
              type="number"
              name="endCoordinates.depth"
              placeholder="Depth"
              value={formData.position.endCoordinates.depth}
              onChange={handleChange}
              className="w-1/3 p-2 bg-gray-800 border border-gray-600 rounded-md text-white"
              required
            />
            <input
              type="number"
              name="endCoordinates.height"
              placeholder="Height"
              value={formData.position.endCoordinates.height}
              onChange={handleChange}
              className="w-1/3 p-2 bg-gray-800 border border-gray-600 rounded-md text-white"
              required
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className={`w-full py-2 font-bold rounded-md text-white ${
              loading
                ? 'bg-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 hover:opacity-80'
            }`}
            disabled={loading}
          >
            {loading ? 'Placing Item...' : 'Place Item'}
          </button>
        </div>
      </form>

      {message && (
        <p
          className={`mt-4 text-center font-medium ${
            message.includes('✅') ? 'text-green-400' : 'text-red-400'
          }`}
        >
          {message}
        </p>
      )}
    </div>
  </div>
</div>

  );
};

export default PlaceItemComponent;
