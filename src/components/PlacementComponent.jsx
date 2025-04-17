import { useState } from 'react';
import { getPlacementRecommendations } from '../services/apiService';

const PlacementComponent = () => {
    const [placementData, setPlacementData] = useState(null);
    const [inputData, setInputData] = useState({
        items: [],
        containers: []
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handlePlacement = async () => {
        setLoading(true);
        setError('');
        try {
            // Format data to match FrontendPlacementInput schema
            const formattedInputData = {
                items: inputData.items.map(item => ({
                    itemId: String(item.itemId),
                    name: item.name,
                    width: parseFloat(item.width),
                    depth: parseFloat(item.depth),
                    height: parseFloat(item.height),
                    mass: parseFloat(item.mass),
                    priority: parseInt(item.priority),
                    preferredZone: item.preferredZone
                })),
                containers: inputData.containers.map(container => ({
                    containerId: container.containerId,
                    zone: container.zone,
                    width: parseFloat(container.width),
                    depth: parseFloat(container.depth),
                    height: parseFloat(container.height)
                }))
            };

            console.log('Sending placement request with data:', formattedInputData);
            const response = await getPlacementRecommendations(formattedInputData);
            console.log('Received placement response:', response);

            if (response.data) {
                setPlacementData(response.data);
                
                if (!response.data.success) {
                    setError('Failed to generate placement recommendations');
                }
            } else {
                setError('Failed to generate placement recommendations');
            }
        } catch (err) {
            console.error("Placement Error:", err);
            console.error("Error details:", err.response?.data || err.message);
            
            // Handle validation errors from FastAPI
            if (err.response?.data?.detail) {
                if (Array.isArray(err.response.data.detail)) {
                    // Multiple validation errors
                    const errorMessages = err.response.data.detail.map(error => 
                        `${error.loc.join('.')}: ${error.msg}`
                    ).join('\n');
                    setError(errorMessages);
                } else if (typeof err.response.data.detail === 'object') {
                    // Single validation error object
                    setError(`${err.response.data.detail.loc.join('.')}: ${err.response.data.detail.msg}`);
                } else {
                    // Simple error message
                    setError(err.response.data.detail);
                }
            } else {
                setError(err.message || 'Failed to process placement request');
            }
        }
        setLoading(false);
    };

    const handleJsonInput = (e) => {
        try {
            const data = JSON.parse(e.target.value);
            console.log('Parsed JSON input:', data);
            if (!data.items || !Array.isArray(data.items)) {
                throw new Error('Invalid items format');
            }
            if (!data.containers || !Array.isArray(data.containers)) {
                throw new Error('Invalid containers format');
            }

            setInputData(data);
            setError('');
        } catch (err) {
            console.error('JSON parsing error:', err);
            setError('Invalid JSON format. Please provide both items and containers arrays.');
        }
    };

    return (
        <div
            className="max-w-2xl mx-auto relative overflow-hidden z-10 bg-gray-800 p-8 rounded-lg shadow-md
                       before:w-24 before:h-24 before:absolute before:bg-purple-600 before:rounded-full before:-z-10 before:blur-2xl
                       after:w-32 after:h-32 after:absolute after:bg-sky-400 after:rounded-full after:-z-10 after:blur-xl after:top-24 after:-right-12"
        >
            <h2 className="text-2xl font-bold text-white mb-6">Cargo Placement</h2>

            <form onSubmit={(e) => { e.preventDefault(); handlePlacement(); }} method="post">
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                        Input Data (JSON format)
                    </label>
                    <textarea
                        placeholder={`{
  "items": [
    {
      "itemId": "1",
      "name": "Item 1",
      "width": 10,
      "depth": 10,
      "height": 10,
      "mass": 5,
      "priority": 1,
      "preferredZone": "A"
    }
  ],
  "containers": [
    {
      "containerId": "C1",
      "zone": "A",
      "width": 100,
      "depth": 100,
      "height": 100
    }
  ]
}`}
                        onChange={handleJsonInput}
                        className="mt-1 p-2 w-full h-96 bg-gray-700 border border-gray-600 rounded-md text-white font-mono text-sm"
                    />
                </div>

                <div className="flex justify-end">
                    <button
                        type="submit"
                        disabled={loading || !inputData.items.length || !inputData.containers.length}
                        className={`bg-gradient-to-r from-purple-600 via-purple-400 to-blue-500 text-white px-4 py-2 font-bold rounded-md hover:opacity-80 ${
                            (loading || !inputData.items.length || !inputData.containers.length) && 'opacity-50 cursor-not-allowed'
                        }`}
                    >
                        {loading ? 'Processing...' : 'Generate Placement'}
                    </button>
                </div>
            </form>

            {error && (
                <div className="mt-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-md whitespace-pre-wrap">
                    {error}
                </div>
            )}

            {placementData && placementData.success && (
                <div className="mt-4 p-3 bg-green-100 border border-green-300 text-green-700 rounded-md">
                    Placement successful! Generated {placementData.placements.length} placement(s).
                </div>
            )}

            {placementData && (
                <div className="mt-6">
                    <h3 className="text-lg font-semibold text-white mb-2">Placement Results</h3>

                    <div className="bg-gray-700 text-white rounded-md shadow p-4 mb-4">
                        <h4 className="font-medium mb-2">Placements ({placementData.placements.length})</h4>
                        <div className="overflow-x-auto">
                            <table className="min-w-full table-auto border-collapse">
                                <thead>
                                    <tr className="bg-gray-50">
                                        <th className="px-4 py-2 border text-gray-900">Item ID</th>
                                        <th className="px-4 py-2 border text-gray-900">Container</th>
                                        <th className="px-4 py-2 border text-gray-900">Position</th>
                                        <th className="px-4 py-2 border text-gray-900">Dimensions</th>
                                        <th className="px-4 py-2 border text-gray-900">Rotation</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {placementData.placements.map((placement, index) => (
                                        <tr key={index} className={index % 2 === 0 ? 'bg-white text-gray-900' : 'bg-gray-50 text-gray-900'}>
                                            <td className="px-4 py-2 border">{placement.itemId}</td>
                                            <td className="px-4 py-2 border">{placement.containerId}</td>
                                            <td className="px-4 py-2 border">
                                                <div className="text-sm">
                                                    <div>Start:</div>
                                                    <div className="ml-2">
                                                        W: {placement.position.startCoordinates.width},
                                                        D: {placement.position.startCoordinates.depth},
                                                        H: {placement.position.startCoordinates.height}
                                                    </div>
                                                    <div className="mt-1">End:</div>
                                                    <div className="ml-2">
                                                        W: {placement.position.endCoordinates.width},
                                                        D: {placement.position.endCoordinates.depth},
                                                        H: {placement.position.endCoordinates.height}
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2 border">
                                                <div className="text-sm">
                                                    W: {placement.position.endCoordinates.width - placement.position.startCoordinates.width}
                                                    <br />
                                                    D: {placement.position.endCoordinates.depth - placement.position.startCoordinates.depth}
                                                    <br />
                                                    H: {placement.position.endCoordinates.height - placement.position.startCoordinates.height}
                                                </div>
                                            </td>
                                            <td className="px-4 py-2 border">
                                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                                    placement.rotation === 'NO_ROTATION' 
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-blue-100 text-blue-800'
                                                }`}>
                                                    {placement.rotation}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {placementData.rearrangements.length > 0 && (
                        <div className="bg-gray-700 text-white rounded-md shadow p-4">
                            <h4 className="font-medium mb-2">Required Rearrangements ({placementData.rearrangements.length})</h4>
                            <div className="overflow-x-auto">
                                <table className="min-w-full table-auto border-collapse">
                                    <thead>
                                        <tr className="bg-gray-50">
                                            <th className="px-4 py-2 border">Item ID</th>
                                            <th className="px-4 py-2 border">From Position</th>
                                            <th className="px-4 py-2 border">To Position</th>
                                            <th className="px-4 py-2 border">Type</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {placementData.rearrangements.map((rearrangement, index) => (
                                            <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                                <td className="px-4 py-2 border">{rearrangement.itemId}</td>
                                                <td className="px-4 py-2 border">
                                                    <div className="text-sm">
                                                        W: {rearrangement.from.x},
                                                        D: {rearrangement.from.y},
                                                        H: {rearrangement.from.z}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2 border">
                                                    <div className="text-sm">
                                                        W: {rearrangement.to.x},
                                                        D: {rearrangement.to.y},
                                                        H: {rearrangement.to.z}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2 border">
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                                        rearrangement.type === 'final'
                                                        ? 'bg-green-100 text-green-800'
                                                        : 'bg-yellow-100 text-yellow-800'
                                                    }`}>
                                                        {rearrangement.type}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default PlacementComponent;