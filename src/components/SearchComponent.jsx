import { useState } from 'react';
import { searchItem } from '../services/apiService';

const SearchComponent = () => {
  const [searchParams, setSearchParams] = useState({
    itemId: '',
    itemName: '',
    userId: ''
  });
  const [searchResult, setSearchResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showSteps, setShowSteps] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSearchParams(prev => ({
      ...prev,
      [name]: value,
      // Clear the other field when one is being used
      ...(name === 'itemId' && value !== '' ? { itemName: '' } : {}),
      ...(name === 'itemName' && value !== '' ? { itemId: '' } : {})
    }));
  };

  const handleSearch = async () => {
    // Validate that either itemId or itemName is provided
    if (!searchParams.itemId && !searchParams.itemName) {
      setError('Please provide either Item ID or Item Name');
      return;
    }

    setLoading(true);
    setError('');
    setSearchResult(null);
    setShowSteps(false);

    try {
      console.log('Sending search request:', searchParams);
      const response = await searchItem(searchParams);
      console.log('Search response:', response);

      if (response.data && response.data.found) {
        setSearchResult(response.data);
        console.log('Search result item:', response.data.item);
        console.log('Position data:', response.data.item.position);
      } else {
        // Handle specific error messages from the backend
        if (response.data?.message) {
          setError(response.data.message);
        } else if (response.data?.detail) {
          // Handle FastAPI validation errors
          if (Array.isArray(response.data.detail)) {
            const errorMessages = response.data.detail.map(error => 
              `${error.loc.join('.')}: ${error.msg}`
            ).join('\n');
            setError(errorMessages);
          } else if (typeof response.data.detail === 'object') {
            setError(`${response.data.detail.loc.join('.')}: ${response.data.detail.msg}`);
          } else {
            setError(response.data.detail);
          }
        } else {
          setError('Item not found');
        }
      }
    } catch (err) {
      console.error('Search error:', err);
      // Handle different error response formats
      if (err.response?.data?.message) {
        setError(err.response.data.message);
      } else if (err.response?.data?.detail) {
        // Handle FastAPI validation errors
        if (Array.isArray(err.response.data.detail)) {
          const errorMessages = err.response.data.detail.map(error => 
            `${error.loc.join('.')}: ${error.msg}`
          ).join('\n');
          setError(errorMessages);
        } else if (typeof err.response.data.detail === 'object') {
          setError(`${err.response.data.detail.loc.join('.')}: ${err.response.data.detail.msg}`);
        } else {
          setError(err.response.data.detail);
        }
      } else {
        setError('Failed to search for item');
      }
    }
    setLoading(false);
  };

  const handleShowSteps = () => {
    setShowSteps(!showSteps);
  };

  return (
    <div className="p-8 bg-gray-800 shadow-md rounded-lg w-full max-w-2xl mx-auto relative overflow-hidden z-10 before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12">
  <h2 className="text-2xl font-bold text-white mb-6">Search Item</h2>

  <div className="space-y-4 mb-6">
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">
        Item ID
      </label>
      <input
        type="text"
        name="itemId"
        value={searchParams.itemId}
        onChange={handleInputChange}
        placeholder="Enter Item ID"
        className={`mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white ${
          searchParams.itemName ? 'opacity-50 cursor-not-allowed' : ''
        }`}
        disabled={searchParams.itemName !== ''}
      />
    </div>

    <div className="relative">
      <label className="block text-sm font-medium text-gray-300 mb-1">
        Item Name
      </label>
      <input
        type="text"
        name="itemName"
        value={searchParams.itemName}
        onChange={handleInputChange}
        placeholder="Enter Item Name"
        className={`mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white ${
          searchParams.itemId ? 'opacity-50 cursor-not-allowed' : ''
        }`}
        disabled={searchParams.itemId !== ''}
      />
      <p className="text-xs text-gray-400 mt-1">
        Enter either Item ID or Item Name, not both
      </p>
    </div>

    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">
        User ID (Optional)
      </label>
      <input
        type="text"
        name="userId"
        value={searchParams.userId}
        onChange={handleInputChange}
        placeholder="Enter User ID"
        className="mt-1 p-2 w-full bg-gray-700 border border-gray-600 rounded-md text-white"
      />
    </div>
  </div>

  <button
    onClick={handleSearch}
    disabled={loading || (!searchParams.itemId && !searchParams.itemName)}
    className={`bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white py-2 px-4 rounded-md w-full font-bold transition-opacity ${
      loading || (!searchParams.itemId && !searchParams.itemName)
        ? 'opacity-50 cursor-not-allowed'
        : 'hover:opacity-80'
    }`}
  >
    {loading ? 'Searching...' : 'Search'}
  </button>

  {error && (
    <div className="mb-4 p-3 bg-red-800 border border-red-600 text-red-100 rounded-md mt-4">
      {error}
    </div>
  )}

  {searchResult && (
    <div className="mt-6 space-y-4">
      <div className="bg-gray-900 rounded-md shadow p-6 text-white">
        <h3 className="text-lg font-semibold mb-3">Item Details</h3>
        <div className="space-y-2">
          <p><strong>Name:</strong> {searchResult.item.name}</p>
          <p><strong>Container ID:</strong> {searchResult.item.containerId}</p>
          <p><strong>Zone:</strong> {searchResult.item.zone}</p>

          <div className="mt-3">
            <p><strong>Position:</strong></p>
            <div className="mt-2 text-sm text-gray-300">
              <p><strong>Start:</strong></p>
              <p className="ml-4">
                Width: {searchResult.item.position.startCoordinates.width}cm,{' '}
                Depth: {searchResult.item.position.startCoordinates.depth}cm,{' '}
                Height: {searchResult.item.position.startCoordinates.height}cm
              </p>
              <p className="mt-2"><strong>End:</strong></p>
              <p className="ml-4">
                Width: {searchResult.item.position.endCoordinates.width}cm,{' '}
                Depth: {searchResult.item.position.endCoordinates.depth}cm,{' '}
                Height: {searchResult.item.position.endCoordinates.height}cm
              </p>
            </div>
          </div>

          <button
            onClick={handleShowSteps}
            className={`mt-4 w-full py-2 px-4 rounded-md text-white font-bold transition-colors ${
              showSteps
                ? 'bg-gray-600 hover:bg-gray-500'
                : 'bg-green-600 hover:bg-green-500'
            }`}
          >
            {showSteps ? 'Hide Retrieval Steps' : 'Show Retrieval Steps'}
          </button>

          {showSteps && searchResult.retrieval_steps?.length > 0 && (
            <div className="mt-4 p-4 bg-gray-700 rounded-md border border-gray-600 text-sm">
              <h4 className="font-medium mb-2 text-white">Retrieval Steps:</h4>
              <ol className="list-decimal list-inside space-y-2 text-gray-200">
                {searchResult.retrieval_steps.map((step, index) => (
                  <li key={index}>
                    <span className="font-medium">{step.action}:</span> {step.item_name}
                    {step.action === 'move' && (
                      <div className="ml-4 text-gray-400">
                        From: Container {step.from_container}<br />
                        To: Container {step.to_container}
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {showSteps && (!searchResult.retrieval_steps || searchResult.retrieval_steps.length === 0) && (
            <div className="mt-4 p-3 bg-yellow-800 border border-yellow-600 text-yellow-100 rounded-md">
              No retrieval steps are needed for this item.
            </div>
          )}
        </div>
      </div>
    </div>
  )}
</div>

  );
};

export default SearchComponent;