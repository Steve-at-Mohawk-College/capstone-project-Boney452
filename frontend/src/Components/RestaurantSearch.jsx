import { useState } from "react";
import axios from "axios";

function RestaurantSearch({ onSignOut }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiUsage, setApiUsage] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setError("");
    setSearchResults([]);

    try {
      // Search for restaurants using Google Places API
      const response = await axios.post("http://localhost:5002/google-search", {
        query: `restaurants in ${searchQuery}`,
        location: searchQuery
      });

      if (response.data.places) {
        setSearchResults(response.data.places);
        setApiUsage(response.data.api_usage);
      }
    } catch (err) {
      setError("Failed to search restaurants. Please try again.");
      console.error("Search error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const addRestaurantToDatabase = async (placeId) => {
    try {
      const response = await axios.post("http://localhost:5002/add-google-place", {
        place_id: placeId
      });
      
      if (response.data.restaurant) {
        alert(`Restaurant "${response.data.restaurant.Name}" added to database successfully!`);
        // Update API usage
        if (response.data.api_usage) {
          setApiUsage(response.data.api_usage);
        }
      }
    } catch (err) {
      if (err.response?.data?.error?.includes("already exists")) {
        alert("This restaurant is already in the database!");
      } else {
        alert("Failed to add restaurant to database. Please try again.");
      }
      console.error("Add restaurant error:", err);
    }
  };

  return (
    <div className="w-full h-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="w-full max-w-4xl">
        {/* Header */}
        <div className="text-center mb-16" style={{marginBottom: '4rem'}}>
          <h1 className="text-5xl font-bold text-slate-900 mb-6 tracking-tight" style={{fontSize: '3rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '1.5rem'}}>Discover Amazing Restaurants</h1>
          <p className="text-slate-600 text-xl font-medium mb-2" style={{color: '#475569', fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.5rem'}}>Find the best restaurants in any city around the world</p>
          <p className="text-slate-500 text-base" style={{color: '#64748b', fontSize: '1rem'}}>Search by location and discover new culinary experiences</p>
        </div>

        {/* Search Form */}
        <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30" style={{backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '1.5rem', padding: '3rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-2" style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#0f172a'}}>Search Restaurants</h2>
          </div>
            
          <form onSubmit={handleSearch} className="space-y-8" style={{display: 'flex', flexDirection: 'column', gap: '2rem'}}>
            {/* Search Field */}
            <div className="space-y-4" style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
              <input
                id="searchQuery"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter city name (e.g., New York, London, Tokyo, Paris)"
                className="w-full px-5 py-4 border-2 border-slate-200 rounded-xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-300 bg-slate-50/50 focus:bg-white shadow-sm hover:shadow-md"
                style={{width: '100%', padding: '1rem 1.25rem', border: '2px solid #e2e8f0', borderRadius: '0.75rem', backgroundColor: 'rgba(248, 250, 252, 0.5)'}}
                disabled={isLoading}
              />
            </div>

            {/* Submit Button */}
            <div className="pt-8" style={{paddingTop: '2rem'}}>
              <button
                type="submit"
                disabled={isLoading || !searchQuery.trim()}
                className="w-full py-5 px-8 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white rounded-xl hover:from-blue-700 hover:via-blue-800 hover:to-indigo-800 focus:ring-4 focus:ring-blue-500/30 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98]"
                style={{width: '100%', padding: '1.25rem 2rem', backgroundColor: '#2563eb', color: 'white', borderRadius: '0.75rem', fontSize: '1.125rem', fontWeight: '600', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}
              >
                {isLoading ? "Searching..." : "Search Restaurants"}
              </button>
            </div>
          </form>

          {error && (
            <div className="bg-red-50/80 border-2 border-red-200 rounded-xl p-4 shadow-sm">
              <p className="text-sm font-semibold text-red-800">{error}</p>
            </div>
          )}
        </div>
      </div>

      {/* Results Section */}
      {searchResults.length > 0 && (
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              🍽️ Found {searchResults.length} Amazing Restaurants
            </h2>
            <p className="text-xl text-slate-600">
              Discovered in <span className="font-semibold text-blue-600">{searchQuery}</span>
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {searchResults.map((restaurant, index) => (
              <div key={restaurant.place_id || index} className="group bg-white/95 backdrop-blur-sm rounded-3xl shadow-xl p-6 border border-white/30 hover:shadow-2xl transition-all duration-500 transform hover:scale-[1.02] hover:-translate-y-2">
                <div className="space-y-5">
                  {/* Restaurant Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="text-xl font-bold text-slate-900 mb-2 group-hover:text-blue-600 transition-colors duration-300">
                        {restaurant.name}
                      </h4>
                      <div className="flex items-center space-x-2 mb-3">
                        <div className="flex items-center">
                          <span className="font-bold text-slate-700 text-lg">
                            ⭐ {restaurant.rating ? restaurant.rating.toFixed(1) : "N/A"}
                          </span>
                        </div>
                        {restaurant.price_level && (
                          <div className="text-slate-600 ml-2">
                            {Array.from({ length: restaurant.price_level }, (_, i) => "💰").join("")}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
                      {restaurant.name.charAt(0)}
                    </div>
                  </div>
                  
                  {/* Address */}
                  <div className="flex items-start space-x-3">
                    <p className="text-sm text-slate-600 leading-relaxed">
                      📍 {restaurant.formatted_address}
                    </p>
                  </div>
                  
                  {/* Types */}
                  {restaurant.types && restaurant.types.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {restaurant.types.slice(0, 3).map((type, idx) => (
                        <span key={idx} className="px-3 py-1 bg-gradient-to-r from-blue-100 to-purple-100 text-blue-800 text-xs rounded-full font-medium border border-blue-200">
                          {type.replace(/_/g, " ").toUpperCase()}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  {/* Add to Database Button */}
                  <button
                    onClick={() => addRestaurantToDatabase(restaurant.place_id)}
                    className="w-full py-3 px-6 bg-gradient-to-r from-green-500 via-emerald-500 to-teal-600 text-white rounded-2xl hover:from-green-600 hover:via-emerald-600 hover:to-teal-700 focus:ring-4 focus:ring-green-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Add to Database
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {searchResults.length === 0 && !isLoading && searchQuery && (
        <div className="max-w-4xl mx-auto px-4 py-16">
          <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30 text-center">
            <div className="text-8xl mb-6">🔍</div>
            <h3 className="text-3xl font-bold text-slate-900 mb-4">No restaurants found</h3>
            <p className="text-xl text-slate-600 mb-8 max-w-2xl mx-auto">
              We couldn't find any restaurants in <span className="font-semibold text-blue-600">{searchQuery}</span>. 
              Try searching for a different city or check your spelling.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => setSearchQuery("")}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-2xl hover:from-blue-600 hover:to-indigo-700 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
              >
                Try Another Search
              </button>
              <button
                onClick={() => setSearchQuery("New York")}
                className="px-6 py-3 bg-gradient-to-r from-slate-500 to-slate-600 text-white rounded-2xl hover:from-slate-600 hover:to-slate-700 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl transform hover:scale-[1.02]"
              >
                Search New York
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RestaurantSearch;
