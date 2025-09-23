import { useEffect } from "react";
import axios from "axios";

function App() {
  useEffect(() => {
    axios.get("http://127.0.0.1:5002/restaurants")
      .then(res => {
        console.log(res.data); // ✅ backend data will show in browser console
      })
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Flavor Quest 🍽️</h1>
      <p>Open your browser console to see the API response.</p>
    </div>
  );
}

export default App;
