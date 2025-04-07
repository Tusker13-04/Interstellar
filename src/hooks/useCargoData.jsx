import { useState } from 'react';

const useCargoData = () => {
  const [containers, setContainers] = useState([]);
  const [items, setItems] = useState([]);

  const addContainer = (container) => {
    setContainers([...containers, { ...container, usedSpace: 0, items: [] }]);
  };

  const addItem = (item) => {
    setItems([...items, { ...item, size: item.width * item.depth * item.height }]);
  };

  return { containers, items, addContainer, addItem };
};

export default useCargoData;