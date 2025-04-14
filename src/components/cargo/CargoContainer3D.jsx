import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Box, Text, Html } from '@react-three/drei';
import * as THREE from 'three';
import { getContainerItems } from '../../services/apiService';

const ClippedBox = ({ position, args, color, opacity, wireframe = false, containerDimensions }) => {
  const clippingPlanes = [
    // Left plane (x = 0)
    new THREE.Plane(new THREE.Vector3(1, 0, 0), 0),
    // Right plane (x = width)
    new THREE.Plane(new THREE.Vector3(-1, 0, 0), containerDimensions.width),
    // Bottom plane (y = 0)
    new THREE.Plane(new THREE.Vector3(0, 1, 0), 0),
    // Top plane (y = height)
    new THREE.Plane(new THREE.Vector3(0, -1, 0), containerDimensions.height),
    // Front plane (z = 0)
    new THREE.Plane(new THREE.Vector3(0, 0, 1), 0),
    // Back plane (z = depth)
    new THREE.Plane(new THREE.Vector3(0, 0, -1), containerDimensions.depth)
  ];

  return (
    <Box args={args} position={position}>
      <meshStandardMaterial
        color={color}
        transparent
        opacity={opacity}
        wireframe={wireframe}
        clippingPlanes={clippingPlanes}
        depthWrite={true}
        side={THREE.DoubleSide}
      />
    </Box>
  );
};

const CargoContainer3D = () => {
  const [containers, setContainers] = useState([]);
  const [selectedContainer, setSelectedContainer] = useState('');
  const [containerItems, setContainerItems] = useState([]);
  const [containerDimensions, setContainerDimensions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showTable, setShowTable] = useState(false);
  const tableRef = useRef(null);

  // Helper function to check if two items overlap
  const doItemsOverlap = (item1, item2) => {
    return !(
      item1.end_width_cm <= item2.start_width_cm ||
      item1.start_width_cm >= item2.end_width_cm ||
      item1.end_depth_cm <= item2.start_depth_cm ||
      item1.start_depth_cm >= item2.end_depth_cm ||
      item1.end_height_cm <= item2.start_height_cm ||
      item1.start_height_cm >= item2.end_height_cm
    );
  };

  // Helper function to adjust item position to avoid overlap
  const adjustItemPosition = (item, existingItems, containerDims) => {
    const itemWidth = item.end_width_cm - item.start_width_cm;
    const itemDepth = item.end_depth_cm - item.start_depth_cm;
    const itemHeight = item.end_height_cm - item.start_height_cm;
    
    let bestPosition = null;
    let minWaste = Infinity;

    // Try different positions with small increments
    const increment = 1; // 1cm increment
    const maxX = containerDims.width - itemWidth;
    const maxY = containerDims.height - itemHeight;
    const maxZ = containerDims.depth - itemDepth;

    for (let x = 0; x <= maxX; x += increment) {
      for (let z = 0; z <= maxZ; z += increment) {
        // Start from bottom up for better stability
        for (let y = 0; y <= maxY; y += increment) {
          const testItem = {
            start_width_cm: x,
            end_width_cm: x + itemWidth,
            start_depth_cm: z,
            end_depth_cm: z + itemDepth,
            start_height_cm: y,
            end_height_cm: y + itemHeight
          };

          // Check if this position overlaps with any existing item
          let hasOverlap = false;
          for (const existingItem of existingItems) {
            if (doItemsOverlap(testItem, existingItem)) {
              hasOverlap = true;
              break;
            }
          }

          if (!hasOverlap) {
            // Calculate waste (distance from origin and other items)
            const waste = x + y + z;
            if (waste < minWaste) {
              minWaste = waste;
              bestPosition = testItem;
            }
          }
        }
      }
    }

    if (bestPosition) {
      return {
        ...item,
        start_width_cm: bestPosition.start_width_cm,
        end_width_cm: bestPosition.end_width_cm,
        start_depth_cm: bestPosition.start_depth_cm,
        end_depth_cm: bestPosition.end_depth_cm,
        start_height_cm: bestPosition.start_height_cm,
        end_height_cm: bestPosition.end_height_cm
      };
    }

    return item; // Return original item if no valid position found
  };

  // Adjust coordinates of all items to prevent overlap
  const adjustAllItemPositions = (items, containerDims) => {
    if (!items || !containerDims) return items;

    const adjustedItems = [];
    
    // Sort items by volume (largest first) for better packing
    const sortedItems = [...items].sort((a, b) => {
      const volumeA = (a.end_width_cm - a.start_width_cm) * 
                     (a.end_depth_cm - a.start_depth_cm) * 
                     (a.end_height_cm - a.start_height_cm);
      const volumeB = (b.end_width_cm - b.start_width_cm) * 
                     (b.end_depth_cm - b.start_depth_cm) * 
                     (b.end_height_cm - b.start_height_cm);
      return volumeB - volumeA;
    });

    for (const item of sortedItems) {
      const adjustedItem = adjustItemPosition(item, adjustedItems, containerDims);
      adjustedItems.push(adjustedItem);
    }

    return adjustedItems;
  };

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
            
            // Adjust item positions before setting state
            const adjustedItems = adjustAllItemPositions(items[containers[0]], dimensions[containers[0]]);
            setContainerItems(adjustedItems || []);
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
            
            // Adjust item positions before setting state
            const adjustedItems = adjustAllItemPositions(items[selectedContainer], dimensions[selectedContainer]);
            setContainerItems(adjustedItems || []);
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
        <Canvas 
          camera={{ position: [cameraDistance, cameraDistance, cameraDistance], fov: 50 }}
          gl={{ 
            localClippingEnabled: true,
            antialias: true,
          }}
        >
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
              side={THREE.DoubleSide}
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
            
            // Add slight offset to prevent z-fighting
            const epsilon = 0.01 * index;

            return (
              <group key={`${item.item_id}-${index}`}>
                {/* Main item box */}
                <ClippedBox
                  args={[width, height, depth]}
                  position={[positionX, positionY, positionZ]}
                  color={`hsl(${hue}, 70%, 60%)`}
                  opacity={0.8}
                  containerDimensions={containerDimensions}
                />
                
                {/* Wireframe outline */}
                <ClippedBox
                  args={[width + 0.1, height + 0.1, depth + 0.1]}
                  position={[positionX, positionY, positionZ]}
                  color={`hsl(${hue}, 90%, 40%)`}
                  opacity={0.4}
                  wireframe={true}
                  containerDimensions={containerDimensions}
                />
              </group>
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
