import SideNavBar from "../components/dashboard/sideNavBar";
import LogsComponent from '../components/LogsComponent';

function Home() {
  return (
    <div>
      <div className="hidden md:block md:w-64 bg-white shadow-md h-full fixed">
        <SideNavBar />
      </div>

      <div className="flex-1 flex flex-col items-center justify-start p-10 ml-64 space-y-6">

        <div className="bg-white shadow-lg rounded-lg p-6 w-full max-w-3xl">
          <LogsComponent />
        </div>

      </div>
    </div>
  );
}

export default Home;
