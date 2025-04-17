import React from "react";
import CargoContainer3D from "./CargoContainer3D";


function CargoManager () {
  return (
    <div className="p-4 rounded-md">

      <h3 className="text-lg font-semibold mt-4 text-white">3D Visualization</h3>
      <div className="w-full h-[800px]">
        <CargoContainer3D/>
      </div>

    </div>
  );
};

export default CargoManager;
