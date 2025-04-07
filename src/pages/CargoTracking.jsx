import SideNavBar from "../components/dashboard/sideNavBar";
import CargoManager from "../components/cargo/CargoManager";

function CargoTracking() {
  return (
    <div className="flex">
      <div className="hidden md:block md:w-64 bg-slate-50 h-screen fixed">
        <SideNavBar />
      </div>

      <div className="flex-1 ml-64 p-4">
        <CargoManager />
      </div>
    </div>
  );
}

export default CargoTracking;
