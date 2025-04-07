import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Dashboard API
export const getDashboardStats = async () => {
  try {
    const response = await api.get('/dashboard/stats');
    console.log('Dashboard API Response:', response);
    return response.data;
  } catch (error) {
    console.error('Dashboard API Error:', error);
    throw error;
  }
};

// Placement Recommendation API
export const getPlacementRecommendations = async (data) => {
  try {
    // Ensure data matches FrontendPlacementInput schema
    const transformedData = {
      items: data.items.map(item => ({
        itemId: String(item.itemId),
        name: item.name,
        width: parseFloat(item.width),
        depth: parseFloat(item.depth),
        height: parseFloat(item.height),
        mass: parseFloat(item.mass),
        priority: parseInt(item.priority),
        preferredZone: item.preferredZone
      })),
      containers: data.containers.map(container => ({
        containerId: container.containerId,
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

// Search and Retrieval APIs
export const searchItem = async (params) => {
  const requestParams = {
    ...(params.itemId && { itemId: parseInt(params.itemId) }),
    ...(params.itemName && { name: params.itemName }),
    ...(params.userId && { userId: params.userId })
  };
  
  try {
    const response = await api.get('/search', { params: requestParams });
    console.log('Search API Response:', response.data);
    return response;
  } catch (error) {
    console.error('Search API Error:', error.response?.data || error);
    throw error;
  }
};

export const retrieveItem = async (data) => {
  try {
    // Ensure itemId is provided and is a valid number
    if (!data.itemId) {
      throw new Error('Item ID is required');
    }

    const requestData = {
      itemId: parseInt(data.itemId),
      timestamp: data.timestamp || new Date().toISOString()
    };

    // Only add userId if it's provided and not empty
    if (data.userId && data.userId.trim()) {
      requestData.userId = data.userId.trim();
    }

    const response = await api.post('/retrieve', requestData);
    console.log('Retrieve API Response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Retrieve API Error:', error.response?.data || error);
    // Format validation errors
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      if (Array.isArray(detail)) {
        const errorMsg = detail.map(err => {
          const field = err.loc[err.loc.length - 1];
          return `${field}: ${err.msg}`;
        }).join(', ');
        throw new Error(errorMsg);
      } else if (typeof detail === 'object' && detail.loc) {
        const field = detail.loc[detail.loc.length - 1];
        throw new Error(`${field}: ${detail.msg}`);
      } else {
        throw new Error(detail.toString());
      }
    }
    throw error;
  }
};

export const placeItem = async (data) => {
  return api.post('/place', data);
};

// Waste Management APIs
export const identifyWaste = async () => {
  return api.get('/waste/identify');
};

export const returnWastePlan = async (data) => {
  return api.post('/waste/return-plan', {
    undocking_container_id: data.undockingContainerId,
    undocking_date: data.undockingDate,
    max_weight: data.maxWeight
  });
};

export const completeUndocking = async (data) => {
  try {
    const response = await api.post('/waste/complete-undocking', {
      undocking_container_id: data.undockingContainerId,
      timestamp: data.timestamp
    });
    console.log('Complete undocking API response:', response.data);
    return response;
  } catch (error) {
    console.error('Complete undocking API error:', error.response?.data || error);
    throw error;
  }
};

// Time Simulation API
export const simulateDays = async (data) => {
  try {
    // The data is already in the correct format, just pass it through
    console.log('Sending request with body:', JSON.stringify(data, null, 2));
    const response = await api.post('/simulate/day', data);
    console.log('Simulation API Response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Simulation API Error:', error.response?.data || error);
    throw error;
  }
};

// Import/Export APIs
export const importItems = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/import/items', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const importContainers = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/import/containers', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const exportArrangement = async () => {
  try {
    const response = await api.get('/export/arrangement', {
      responseType: 'blob'
    });
    
    // Get the filename from the Content-Disposition header
    const contentDisposition = response.headers['content-disposition'];
    const filename = contentDisposition
      ? contentDisposition.split('filename=')[1].replace(/"/g, '')
      : 'cargo_arrangement.csv';
    
    // Create a download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    return { success: true };
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

// Logging API
export const getLogs = async (startDate, endDate, filters = {}) => {
  // Format dates to ISO string with UTC timezone
  const formattedStartDate = new Date(startDate).toISOString();
  const formattedEndDate = new Date(endDate).toISOString();

  // Prepare params object
  const params = {
    startDate: formattedStartDate,
    endDate: formattedEndDate
  };

  // Add filters if they have values
  if (filters.itemId) params.item_id = filters.itemId;
  if (filters.userId) params.user_id = filters.userId;
  if (filters.actionType) params.action_type = filters.actionType;

  return api.get('/logs', { params });
};

export const clearLogs = async () => {
  try {
    const response = await api.post('/logs/clear');
    return response.data;
  } catch (error) {
    console.error('API Error:', error);
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      throw new Error(error.response.data.detail || 'Failed to clear logs');
    } else if (error.request) {
      // The request was made but no response was received
      throw new Error('No response received from server');
    } else {
      // Something happened in setting up the request that triggered an Error
      throw new Error('Error setting up the request');
    }
  }
};

// Container 3D Visualization APIs
export const updateContainer3D = async (placementData) => {
  try {
    const response = await api.post('/container3d/update', placementData);
    return response.data;
  } catch (error) {
    console.error('Container 3D Update Error:', error);
    throw error;
  }
};

export const getContainer3DData = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/container3d/data`);
    if (response.data) {
      return {
        data: {
          dimensions: response.data.dimensions || {
            width: 0,
            height: 0,
            depth: 0
          },
          items: response.data.items || []
        }
      };
    }
    throw new Error('Invalid response format');
  } catch (error) {
    console.error('Error fetching container 3D data:', error);
    throw error;
  }
};

export const getContainerItems = async (containerId) => {
  try {
    const params = {};
    if (containerId) {
      params.containerId = containerId;
    }
    
    const response = await api.get('/visualization/containers', { params });
    console.log('Visualization API Response:', response.data);
    return response;
  } catch (error) {
    console.error('Visualization API Error:', error.response?.data || error);
    throw error;
  }
};
