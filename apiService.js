const API_BASE_URL = 'http://host.docker.internal:8000/api'; // Use the service name defined in Docker Compose

export const getPlacementRecommendations = async (data) => {
  try {
    // Ensure data matches FrontendPlacementInput schema
    const transformedData = {
      items: data.items.map(item => ({
        itemId: item.itemId,
        name: item.name,
        width: parseFloat(item.width),
        depth: parseFloat(item.depth),
        height: parseFloat(item.height),
        mass: parseFloat(item.mass),
        priority: parseInt(item.priority),
        preferredZone: item.preferredZone
      })),
      containers: data.containers.map(container => ({
        containerId: container.containerId || container.zone,
        zone: container.zone,
        width: parseFloat(container.width),
        depth: parseFloat(container.depth),
        height: parseFloat(container.height)
      }))
    };

    console.log('Transformed data:', transformedData);
    const response = await api.post('/placement', transformedData);

    // Ensure response matches expected format
    return {
      data: {
        success: response.data.success || false,
        placements: response.data.placements || [],
        rearrangements: response.data.rearrangements || []
      }
    };
  } catch (error) {
    console.error('Placement API Error:', error);
    throw error;
  }
};