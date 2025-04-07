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
      [name]: value
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
    <div className="p-6 bg-gray-100 shadow-md rounded-md w-full max-w-2xl">
      <h2 className="text-xl font-bold mb-4">Search Item</h2>
      
      <div className="space-y-3 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Item ID
          </label>
          <input
            type="text"
            name="itemId"
            value={searchParams.itemId}
            onChange={handleInputChange}
            placeholder="Enter Item ID"
            className="border p-2 w-full rounded-md"
          />
        </div>

        <div className="relative">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Item Name
          </label>
          <input
            type="text"
            name="itemName"
            value={searchParams.itemName}
            onChange={handleInputChange}
            placeholder="Enter Item Name"
            className="border p-2 w-full rounded-md"
          />
          <p className="text-xs text-gray-500 mt-1">
            Provide either Item ID or Item Name
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            User ID (Optional)
          </label>
          <input
            type="text"
            name="userId"
            value={searchParams.userId}
            onChange={handleInputChange}
            placeholder="Enter User ID"
            className="border p-2 w-full rounded-md"
          />
        </div>
      </div>

      <button
        onClick={handleSearch}
        disabled={loading || (!searchParams.itemId && !searchParams.itemName)}
        className={`bg-blue-500 text-white py-2 px-4 rounded-md w-full mb-4 ${
          loading || (!searchParams.itemId && !searchParams.itemName)
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:bg-blue-600'
        }`}
      >
        {loading ? 'Searching...' : 'Search'}
      </button>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
          {error}
        </div>
      )}

      {searchResult && (
        <div className="mt-4 space-y-4">
          <div className="bg-white rounded-md shadow p-4">
            <h3 className="text-lg font-semibold mb-3">Item Details</h3>
            <div className="space-y-2">
              <p><strong>Name:</strong> {searchResult.item.name}</p>
              <p><strong>Container ID:</strong> {searchResult.item.containerId}</p>
              <p><strong>Zone:</strong> {searchResult.item.zone}</p>

              <div className="mt-2">
                <p><strong>Position:</strong></p>
                <div className="mt-2">
                  <p><strong>Start:</strong></p>
                  <p className="ml-4">
                    Width: {searchResult.item.position.startCoordinates.width}cm,{' '}
                    Depth: {searchResult.item.position.startCoordinates.depth}cm,{' '}
                    Height: {searchResult.item.position.startCoordinates.height}cm
                  </p>
                  <p className="mt-1"><strong>End:</strong></p>
                  <p className="ml-4">
                    Width: {searchResult.item.position.endCoordinates.width}cm,{' '}
                    Depth: {searchResult.item.position.endCoordinates.depth}cm,{' '}
                    Height: {searchResult.item.position.endCoordinates.height}cm
                  </p>
                </div>
              </div>

              <button
                onClick={handleShowSteps}
                className={`mt-4 w-full py-2 px-4 rounded-md text-white transition-colors ${
                  showSteps ? 'bg-gray-500' : 'bg-green-500 hover:bg-green-600'
                }`}
              >
                {showSteps ? 'Hide Retrieval Steps' : 'Show Retrieval Steps'}
              </button>

              {showSteps && searchResult.retrieval_steps && searchResult.retrieval_steps.length > 0 && (
                <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-200">
                  <h4 className="font-medium mb-2">Retrieval Steps:</h4>
                  <ol className="list-decimal list-inside space-y-2">
                    {searchResult.retrieval_steps.map((step, index) => (
                      <li key={index} className="text-sm">
                        <span className="font-medium">{step.action}:</span> {step.item_name}
                        {step.action === 'move' && (
                          <div className="ml-4 text-gray-600">
                            From: Container {step.from_container}<br/>
                            To: Container {step.to_container}
                          </div>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {showSteps && (!searchResult.retrieval_steps || searchResult.retrieval_steps.length === 0) && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-md">
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