import { useNavigate } from "react-router-dom";
import Starfield from "../components/starField";

function Landing() {
  const navigate = useNavigate();

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <Starfield />
      </div>

      <div className="absolute inset-0 flex flex-col items-center justify-center text-white text-center z-10">
        <h1 className="text-4xl md:text-6xl font-bold mb-6">
          CODE FOR THE COSMOS
        </h1>
        <button
          className="relative mt-4 px-8 py-4 text-lg md:text-xl font-bold text-white 
            rounded-lg shadow-lg transition duration-300 
            bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 
            hover:from-indigo-400 hover:via-purple-500 hover:to-pink-400
            border-2 border-transparent hover:border-white 
            before:absolute before:inset-0 before:bg-white before:blur-md before:opacity-20"
          onClick={() => navigate("/home")}
        >
          Explore
        </button>
      </div>
    </div>
  );
}

export default Landing;
