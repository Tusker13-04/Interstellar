import "./App.css";
import Landing from './pages/landing';
import Home from './pages/home';
import CargoTracking from './pages/CargoTracking';
import Placement from './pages/PlacementRecommendation';
import Search from './pages/search';

import Waste from './pages/waste';
import Place from './pages/Place';
import Retreive from './pages/Retreive';
import Time from './pages/TimeSimulation';
import Upload from './pages/ImportExport';
import Logs from './pages/logs';








import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

function App() {
  return (
    <div>
      <Router>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/home" element={<Home/>} />
          <Route path="/cargoTracking" element={<CargoTracking/>} />


          <Route path="/placement" element={<Placement/>} />
          <Route path="/search" element={<Search/>} />
          <Route path="/waste" element={<Waste/>} />
          <Route path="/place" element={<Place/>} />
          <Route path="/retreive" element={<Retreive/>} />
          <Route path="/simulate" element={<Time/>} />
          <Route path="/upload" element={<Upload/>} />
          <Route path="/logs" element={<Logs/>} />






        </Routes>
      </Router>
    </div>
  );
}

export default App;
