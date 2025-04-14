import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Box, Text, Html, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import { getContainerItems } from '../../services/apiService';
import { useThree, useFrame } from '@react-three/fiber';

const ClippedBox = ({ position, args, color, wireframe = false, containerDimensions }) => {
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
        transparent={wireframe}
        opacity={wireframe ? 0.1 : 1}
        wireframe={wireframe}
        clippingPlanes={clippingPlanes}
        depthWrite={!wireframe}
        side={THREE.DoubleSide}
        metalness={0.1}
        roughness={0.7}
      />
    </Box>
  );
};

// Add new component for compass
const CompassOverlay = () => {
  const { camera } = useThree();
  const [rotation, setRotation] = useState(0);

  useFrame(() => {
    const angle = Math.atan2(camera.position.x, camera.position.z);
    setRotation(angle);
  });

  return (
    <Html
      style={{
        position: 'absolute',
        left: '-650px',
        bottom: '-180px',
        background: 'rgba(0,0,0,0.8)',
        padding: '25px',
        borderRadius: '8px',
        color: 'white',
        fontFamily: 'monospace',
        userSelect: 'none',
        boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
        zIndex: 1000
      }}
      prepend
    >
      <div style={{ transform: `rotate(${rotation}rad)` }}>
        <div style={{ 
          position: 'absolute', 
          top: '-20px', 
          left: '50%', 
          transform: 'translateX(-50%)',
          color: '#FF5555',
          fontWeight: 'bold',
          textShadow: '0 0 3px rgba(0,0,0,0.5)'
        }}>N</div>
        <div style={{ 
          position: 'absolute', 
          bottom: '-20px', 
          left: '50%', 
          transform: 'translateX(-50%)',
          color: '#AAAAAA',
          textShadow: '0 0 3px rgba(0,0,0,0.5)'
        }}>S</div>
        <div style={{ 
          position: 'absolute', 
          left: '-20px', 
          top: '50%', 
          transform: 'translateY(-50%)',
          color: '#AAAAAA',
          textShadow: '0 0 3px rgba(0,0,0,0.5)'
        }}>W</div>
        <div style={{ 
          position: 'absolute', 
          right: '-15px', 
          top: '50%', 
          transform: 'translateY(-50%)',
          color: '#AAAAAA',
          textShadow: '0 0 3px rgba(0,0,0,0.5)'
        }}>E</div>
        <div style={{ 
          width: '50px', 
          height: '50px', 
          border: '3px solid rgba(255,255,255,0.4)', 
          borderRadius: '50%', 
          position: 'relative',
          background: 'radial-gradient(circle, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.9) 100%)'
        }}>
          <div style={{ 
            position: 'absolute', 
            top: '50%', 
            left: '50%', 
            width: '2px', 
            height: '20px', 
            background: 'linear-gradient(to top, #FF5555, #FF0000)',
            transformOrigin: 'bottom',
            transform: 'translate(-50%, -100%)',
            boxShadow: '0 0 5px rgba(255,0,0,0.5)'
          }} />
          <div style={{ 
            position: 'absolute', 
            top: '50%', 
            left: '50%', 
            width: '2px', 
            height: '20px', 
            background: '#666',
            transformOrigin: 'top',
            transform: 'translate(-50%, 0%) rotate(180deg)'
          }} />
        </div>
      </div>
    </Html>
  );
};

// Add new component for zoom level
const ZoomLevelOverlay = () => {
  const { camera } = useThree();
  const [zoom, setZoom] = useState(0);

  useFrame(() => {
    const distance = Math.sqrt(
      camera.position.x * camera.position.x +
      camera.position.y * camera.position.y +
      camera.position.z * camera.position.z
    );
    setZoom(distance);
  });

  return (
    <Html
      style={{
        position: 'absolute',
        left: '-650px',
        bottom: '-230px',
        background: 'rgba(0,0,0,0.8)',
        padding: '10px 15px',
        borderRadius: '8px',
        color: 'white',
        fontFamily: 'monospace',
        userSelect: 'none',
        boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
        fontSize: '14px',
        zIndex: 1000
      }}
      prepend
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px', whiteSpace: 'nowrap' }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: '5px' }}>
          <path d="M15 3L21 9M21 9L15 15M21 9H3" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        {zoom.toFixed(1)}x
      </div>
    </Html>
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

    // Try different positions with smaller increments for more precise placement
    const increment = 0.5; // 0.5cm increment for finer positioning
    const maxX = containerDims.width - itemWidth;
    const maxY = containerDims.height - itemHeight;
    const maxZ = containerDims.depth - itemDepth;

    // Add small safety margin to prevent touching edges
    const safetyMargin = 0.1; // 0.1cm margin

    // First try positions next to existing items for better packing
    const potentialPositions = [];
    
    // Add floor level as first potential position
    potentialPositions.push({ x: 0, y: 0, z: 0 });

    // Add positions next to existing items
    existingItems.forEach(existingItem => {
      // Position next to right face
      potentialPositions.push({
        x: existingItem.end_width_cm + safetyMargin,
        y: existingItem.start_height_cm,
        z: existingItem.start_depth_cm
      });
      
      // Position on top
      potentialPositions.push({
        x: existingItem.start_width_cm,
        y: existingItem.end_height_cm + safetyMargin,
        z: existingItem.start_depth_cm
      });
      
      // Position behind
      potentialPositions.push({
        x: existingItem.start_width_cm,
        y: existingItem.start_height_cm,
        z: existingItem.end_depth_cm + safetyMargin
      });
    });

    // Try each potential position first
    for (const pos of potentialPositions) {
      if (pos.x <= maxX && pos.y <= maxY && pos.z <= maxZ) {
        const testItem = {
          start_width_cm: pos.x,
          end_width_cm: pos.x + itemWidth,
          start_depth_cm: pos.z,
          end_depth_cm: pos.z + itemDepth,
          start_height_cm: pos.y,
          end_height_cm: pos.y + itemHeight
        };

        let hasOverlap = false;
        for (const existingItem of existingItems) {
          if (doItemsOverlap(testItem, existingItem)) {
            hasOverlap = true;
            break;
          }
        }

        if (!hasOverlap) {
          // Calculate waste as distance from origin and nearest items
          const waste = pos.x + pos.y + pos.z;
          if (waste < minWaste) {
            minWaste = waste;
            bestPosition = testItem;
          }
        }
      }
    }

    // If no valid position found among potential positions, try grid search
    if (!bestPosition) {
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

            let hasOverlap = false;
            for (const existingItem of existingItems) {
              if (doItemsOverlap(testItem, existingItem)) {
                hasOverlap = true;
                break;
              }
            }

            if (!hasOverlap) {
              // Calculate waste considering all dimensions and distance to other items
              const distanceToItems = existingItems.reduce((minDist, existingItem) => {
                const dx = Math.abs(x - existingItem.end_width_cm);
                const dy = Math.abs(y - existingItem.end_height_cm);
                const dz = Math.abs(z - existingItem.end_depth_cm);
                return Math.min(minDist, dx + dy + dz);
              }, Infinity);

              const waste = (x + y + z) * 0.7 + distanceToItems * 0.3; // Weight both factors
              if (waste < minWaste) {
                minWaste = waste;
                bestPosition = testItem;
              }
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

    // If no valid position found, try to place it at origin with increased safety margin
    const originPosition = {
      ...item,
      start_width_cm: 0,
      end_width_cm: itemWidth,
      start_depth_cm: 0,
      end_depth_cm: itemDepth,
      start_height_cm: 0,
      end_height_cm: itemHeight
    };

    return originPosition;
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
      <div style={{ width: '100%', height: '600px', border: '1px solid #ccc', borderRadius: '4px', overflow: 'hidden', marginBottom: '2rem', position: 'relative' }}>
        <Canvas 
          camera={{ position: [cameraDistance, cameraDistance, cameraDistance], fov: 50 }}
          gl={{ 
            localClippingEnabled: true,
            antialias: true,
          }}
        >
          <ambientLight intensity={0.5} />
          <pointLight position={[cameraDistance, cameraDistance, cameraDistance]} />
          
          {/* Add overlays */}
          <CompassOverlay />
          <ZoomLevelOverlay />
          
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
          {containerItems
            // Sort items by volume (largest first)
            .sort((a, b) => {
              const volumeA = (a.end_width_cm - a.start_width_cm) * 
                            (a.end_depth_cm - a.start_depth_cm) * 
                            (a.end_height_cm - a.start_height_cm);
              const volumeB = (b.end_width_cm - b.start_width_cm) * 
                            (b.end_depth_cm - b.start_depth_cm) * 
                            (b.end_height_cm - b.start_height_cm);
              return volumeB - volumeA;
            })
            // Filter out any items that overlap with previously processed items
            .filter((item, index, items) => {
              // Check if this item overlaps with any previously processed (larger) items
              for (let i = 0; i < index; i++) {
                const previousItem = items[i];
                if (!(
                  item.end_width_cm <= previousItem.start_width_cm ||
                  item.start_width_cm >= previousItem.end_width_cm ||
                  item.end_depth_cm <= previousItem.start_depth_cm ||
                  item.start_depth_cm >= previousItem.end_depth_cm ||
                  item.end_height_cm <= previousItem.start_height_cm ||
                  item.start_height_cm >= previousItem.end_height_cm
                )) {
                  return false; // Skip this item as it overlaps with a larger one
                }
              }
              return true;
            })
            .map((item, index) => {
              // Calculate item dimensions
              const width = item.end_width_cm - item.start_width_cm;
              const height = item.end_height_cm - item.start_height_cm;
              const depth = item.end_depth_cm - item.start_depth_cm;

              // Calculate center position
              const centerX = item.start_width_cm + (width / 2);
              const centerY = item.start_height_cm + (height / 2);
              const centerZ = item.start_depth_cm + (depth / 2);

              // Generate a consistent color based on item ID
              const hue = ((parseInt(item.item_id) || index) * 137.5) % 360;

              return (
                <group key={`${item.item_id}-${index}`}>
                  {/* Main item box - fully opaque */}
                  <ClippedBox
                    args={[width, height, depth]}
                    position={[centerX, centerY, centerZ]}
                    color={`hsl(${hue}, 85%, 50%)`}
                    containerDimensions={containerDimensions}
                  />
                  
                  {/* Wireframe outline - very subtle */}
                  <ClippedBox
                    args={[width + 0.1, height + 0.1, depth + 0.1]}
                    position={[centerX, centerY, centerZ]}
                    color={`hsl(${hue}, 90%, 30%)`}
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
                      ({item.start_width_cm.toFixed(2)}, {item.start_depth_cm.toFixed(2)}, {item.start_height_cm.toFixed(2)})
                    </td>
                    <td className="px-4 py-2 text-white">
                      ({item.end_width_cm.toFixed(2)}, {item.end_depth_cm.toFixed(2)}, {item.end_height_cm.toFixed(2)})
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
