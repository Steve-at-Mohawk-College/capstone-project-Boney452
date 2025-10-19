import { useState, useEffect } from "react";
import axios from "axios";
import RestaurantFlipCard from "./RestaurantFlipCard";

function RestaurantSearch({ onSignOut }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiUsage, setApiUsage] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);


  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setError("");
    setSearchResults([]);
    setHasSearched(true);

        try {
          // Search for restaurants using Google Places API
          const response = await axios.post("http://localhost:5002/google-search", {
            query: `restaurants in ${searchQuery}`,
            location: searchQuery
          });

          if (response.data.places) {
            setSearchResults(response.data.places);
            setApiUsage(response.data.api_usage);
            
            // Automatically add all restaurants to database
            await addAllRestaurantsToDatabase(response.data.places);
          }
        } catch (err) {
          setError("Failed to search restaurants. Please try again.");
          console.error("Search error:", err);
        } finally {
          setIsLoading(false);
        }
  };

  const addAllRestaurantsToDatabase = async (restaurants) => {
    try {
      console.log("Restaurants to add:", restaurants);
      console.log("Number of restaurants:", restaurants.length);
      
      if (!restaurants || restaurants.length === 0) {
        console.log("No restaurants provided, skipping database addition");
        return;
      }
      
      const placeIds = restaurants.map(restaurant => {
        console.log("Restaurant:", restaurant.name, "Place ID:", restaurant.place_id);
        return restaurant.place_id;
      }).filter(id => id);
      
      console.log("Place IDs to send:", placeIds);
      
      if (placeIds.length === 0) {
        console.log("No valid place IDs found, skipping database addition");
        return;
      }
      
      console.log("Sending request to batch-add-restaurants with place_ids:", placeIds);
      
      const response = await axios.post("http://localhost:5002/batch-add-restaurants", {
        place_ids: placeIds
      });
      
      console.log("Batch-add response:", response.data);
      
      if (response.data.success) {
        console.log(`Successfully added ${response.data.added_count} restaurants to database`);
        // Update API usage if provided
        if (response.data.api_usage) {
          setApiUsage(response.data.api_usage);
        }
      }
    } catch (err) {
      console.error("Failed to add restaurants to database:", err);
      console.error("Error response:", err.response?.data);
      console.error("Error status:", err.response?.status);
      // Don't show error to user as this is automatic
    }
  };

  return (
    <div className="w-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dashboard-page">
      {/* Logout Button */}
      <div className="absolute top-4 right-4 z-10" style={{position: 'absolute', top: '1rem', right: '1rem', zIndex: 10}}>
        <button
          onClick={onSignOut}
          className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg transition-colors duration-200 font-semibold"
          style={{backgroundColor: '#ef4444', color: 'white', padding: '0.5rem 1rem', borderRadius: '0.5rem', fontWeight: '600'}}
        >
          Logout
        </button>
      </div>

      {/* Search Section - Always Visible */}
      <div className="w-full max-w-4xl mx-auto px-4 py-12" style={{width: '100%', maxWidth: '56rem', margin: '0 auto', padding: '3rem 1rem'}}>
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



      {/* Results Grid */}
      {searchResults.length > 0 && (
        <div className="w-full max-w-6xl mx-auto px-4 pb-8" style={{width: '100%', maxWidth: '72rem', margin: '0 auto', padding: '0 1rem 2rem'}}>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem'}}>
            {searchResults.map((restaurant, index) => (
              <RestaurantFlipCard
                key={restaurant.place_id || index}
                restaurant={restaurant}
                isSearchResult={true}
                onRatingUpdate={() => {}} // No need to reload since we're only showing search results
              />
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {searchResults.length === 0 && !isLoading && hasSearched && (
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
                onClick={() => {
                  setSearchQuery("");
                  setHasSearched(false);
                }}
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
