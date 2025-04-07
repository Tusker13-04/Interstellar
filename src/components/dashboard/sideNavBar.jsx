import { Button } from "../ui/button";
import menuOptions from "./SideBarMenuOptions";
import { Plus } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

function SideNavBar() {
  const location = useLocation();
  const [activePath, setActivePath] = useState(location.pathname);

  useEffect(() => {
    setActivePath(location.pathname);
  }, [location.pathname]);

  return (
    <div className="w-64 p-6 py-10 h-full border-r border-gray-800 bg-black/80 backdrop-blur-xl shadow-lg">
      <div className="flex justify-center">
        <Link to="/home">
          <div
            className="text-2xl md:text-3xl font-bold tracking-wide font-aeonik"
            style={{ color: "#DBFF00" }}
          >
            INTERSTELLAR
          </div>
        </Link>
      </div>

      <Link to="/cargoTracking">
        <Button className="flex items-center gap-2 w-full mt-8 rounded-full text-lg font-medium transition-all hover:scale-105 text-white">
          <Plus className="w-5 h-5" /> Cargo Tracking
        </Button>
      </Link>

      <hr className="mt-8 mb-8 border-gray-600 w-[90%] mx-auto" />

      <div className="mt-6 flex flex-col gap-4">
        {menuOptions.map((item) => (
          <Link to={item.path} key={item.id}>
            <Button
              variant="ghost"
              className={`w-full flex gap-3 items-center text-lg font-medium px-4 py-3 rounded-lg transition-all duration-300 hover:bg-violet-500/10 hover:text-violet-400
                ${activePath === item.path ? "text-violet-400 bg-violet-500/10" : "text-gray-300"}
              `}
            >
              {item.name}
            </Button>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default SideNavBar;
