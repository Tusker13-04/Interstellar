import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Box, Text } from '@react-three/drei';
import { getContainerItems } from '../../services/apiService';

const CargoContainer3D = () => {
  const [containers, setContainers] = useState([]);
  const [selectedContainer, setSelectedContainer] = useState('');
  const [containerItems, setContainerItems] = useState([]);
  const [containerDimensions, setContainerDimensions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showTable, setShowTable] = useState(false);
  const tableRef = useRef(null);

  const scrollToTable = () => {
    setShowTable(true);
    setTimeout(() => {
      tableRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getContainerItems();

        if (response && response.data && response.data.success) {
          const { containers, items, dimensions } = response.data;
          
          if (containers && containers.length > 0) {
            setContainers(containers);
            setSelectedContainer(containers[0]);
            setContainerItems(items[containers[0]] || []);
            setContainerDimensions(dimensions[containers[0]]);
          } else {
            setError('No containers available for visualization');
          }
        } else {
          const errorMessage = response?.data?.error || 'Failed to fetch container data';
          setError(errorMessage);
        }
      } catch (err) {
        console.error('Error in 3D visualization:', err);
        setError(err.message || 'Failed to fetch container data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (selectedContainer) {
      const fetchContainerData = async () => {
        try {
          setLoading(true);
          setError(null);
          const response = await getContainerItems(selectedContainer);
          
          if (response && response.data && response.data.success) {
            const { items, dimensions } = response.data;
            setContainerItems(items[selectedContainer] || []);
            setContainerDimensions(dimensions[selectedContainer]);
          } else {
            const errorMessage = response?.data?.error || 'Failed to fetch container data';
            setError(errorMessage);
          }
        } catch (err) {
          console.error('Error fetching container items:', err);
          setError(err.message || 'Failed to fetch container items');
        } finally {
          setLoading(false);
        }
      };

      fetchContainerData();
    }
  }, [selectedContainer]);

  // Error message component
  const ErrorMessage = ({ message }) => (
    <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-600">
      <p className="font-semibold mb-2">Error:</p>
      <p>{message}</p>
      <p className="mt-4 text-sm">
        Ensure you have imported containers and placed items using the Import/Export and Placement sections.
      </p>
    </div>
  );

  // Loading indicator
  if (loading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading 3D visualization...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return <ErrorMessage message={error} />;
  }

  // No containers available
  if (!containers.length) {
    return <ErrorMessage message="No containers available for visualization. Please import containers first." />;
  }

  // No container dimensions available
  if (!containerDimensions) {
    return <ErrorMessage message="No container dimensions available. Please ensure containers have valid dimensions." />;
  }

  // Calculate camera position based on container dimensions
  const maxDimension = Math.max(
    containerDimensions.width,
    containerDimensions.height,
    containerDimensions.depth
  );
  const cameraDistance = maxDimension * 2;

  // Calculate container center position
  const containerCenter = {
    x: containerDimensions.width / 2,
    y: containerDimensions.height / 2,
    z: containerDimensions.depth / 2
  };

  return (
    <div className="p-4">
      <div className="mb-4 flex justify-between items-center">
        <div>
          <label className="block text-sm font-medium mb-2">Select Container</label>
          <select
            value={selectedContainer}
            onChange={(e) => {
              setSelectedContainer(e.target.value);
              setShowTable(false);
            }}
            className="w-full p-2 border rounded"
          >
            {containers.map(containerId => (
              <option key={containerId} value={containerId}>
                Container {containerId}
              </option>
            ))}
          </select>
        </div>
        {containerItems.length > 0 && (
          <button
            onClick={scrollToTable}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            View Items List
          </button>
        )}
      </div>

      <div className="mb-4">
        <h3 className="text-sm font-medium">Container Dimensions:</h3>
        <p className="text-sm">
          Width: {containerDimensions.width}cm, 
          Height: {containerDimensions.height}cm, 
          Depth: {containerDimensions.depth}cm
        </p>
        <p className="text-sm mt-2">
          Items in container: <span className="font-semibold">{containerItems.length}</span>
        </p>
      </div>

      {/* 3D Visualization Container */}
      <div style={{ width: '100%', height: '600px', border: '1px solid #ccc', borderRadius: '4px', overflow: 'hidden', marginBottom: '2rem' }}>
        <Canvas camera={{ position: [cameraDistance, cameraDistance, cameraDistance], fov: 50 }}>
          <ambientLight intensity={0.5} />
          <pointLight position={[cameraDistance, cameraDistance, cameraDistance]} />
          
          {/* Container */}
          <Box
            args={[
              containerDimensions.width,
              containerDimensions.height,
              containerDimensions.depth
            ]}
            position={[containerCenter.x, containerCenter.y, containerCenter.z]}
          >
            <meshStandardMaterial 
              color="#888888" 
              wireframe 
              transparent
              opacity={0.2}
            />
          </Box>

          {/* Items */}
          {containerItems.map((item, index) => {
            // Calculate item dimensions
            const width = item.end_width_cm - item.start_width_cm;
            const height = item.end_height_cm - item.start_height_cm;
            const depth = item.end_depth_cm - item.start_depth_cm;

            // Calculate item position (center point)
            const positionX = (item.start_width_cm + item.end_width_cm) / 2;
            const positionY = (item.start_height_cm + item.end_height_cm) / 2;
            const positionZ = (item.start_depth_cm + item.end_depth_cm) / 2;

            // Generate a consistent color based on item ID
            const hue = ((parseInt(item.item_id) || index) * 137.5) % 360;

            return (
              <Box
                key={`${item.item_id}-${index}`}
                args={[width, height, depth]}
                position={[positionX, positionY, positionZ]}
              >
                <meshStandardMaterial 
                  color={`hsl(${hue}, 70%, 60%)`}
                  transparent
                  opacity={0.8}
                />
              </Box>
            );
          })}

          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            autoRotate={false}
          />
          <gridHelper args={[maxDimension * 2, 20]} />
          <axesHelper args={[maxDimension]} />
        </Canvas>
      </div>

      {/* Item Table Section - Separate from visualization */}
      {containerItems.length > 0 && showTable && (
        <div className="border-t pt-8 mt-8" ref={tableRef}>
          <div className="max-h-[400px] overflow-y-auto border rounded">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0">
                <tr className="bg-gray-800">
                  <th className="px-4 py-2 text-left text-white font-semibold">Item ID</th>
                  <th className="px-4 py-2 text-left text-white font-semibold">Start Position (W,D,H)</th>
                  <th className="px-4 py-2 text-left text-white font-semibold">End Position (W,D,H)</th>
                  <th className="px-4 py-2 text-left text-white font-semibold">Dimensions (W×D×H)</th>
                </tr>
              </thead>
              <tbody>
                {containerItems.map((item, index) => (
                  <tr key={`legend-${item.item_id}-${index}`} className="border-t border-gray-200 bg-gray-700 hover:bg-gray-600">
                    <td className="px-4 py-2 text-white">{item.item_id}</td>
                    <td className="px-4 py-2 text-white">
                      ({item.start_width_cm}, {item.start_depth_cm}, {item.start_height_cm})
                    </td>
                    <td className="px-4 py-2 text-white">
                      ({item.end_width_cm}, {item.end_depth_cm}, {item.end_height_cm})
                    </td>
                    <td className="px-4 py-2 text-white">
                      {Math.round(item.end_width_cm - item.start_width_cm)}cm × 
                      {Math.round(item.end_depth_cm - item.start_depth_cm)}cm × 
                      {Math.round(item.end_height_cm - item.start_height_cm)}cm
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default CargoContainer3D; 
