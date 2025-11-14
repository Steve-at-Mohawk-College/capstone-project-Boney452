import { useState } from "react";
import axios from "axios";
import RestaurantFlipCard from "./RestaurantFlipCard";
import { sanitizeInput } from "../utils/security";
import ErrorBoundary from "./ErrorBoundary";
import { API_BASE_URL } from "../config";
import { tokenStorage } from "../utils/tokenStorage";

function RestaurantSearch({ onSignOut, onManageUsers, onOpenChat, isAdmin }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    
    // Sanitize search query
    const sanitizedQuery = sanitizeInput(searchQuery, 200);
    if (!sanitizedQuery) {
      setError("Please enter a valid search query");
      return;
    }
    
    setIsLoading(true);
    setError("");
    setSearchResults([]);
    setHasSearched(true);

    try {
      const token = tokenStorage.get();
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(
        `${API_BASE_URL}/google-search`,
        { query: `restaurants in ${sanitizedQuery}`, location: sanitizedQuery },
        { headers }
      );
      if (res.data.places) {
        setSearchResults(res.data.places);
      }
    } catch (err) {
      setError("Failed to search restaurants. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestaurantDataUpdate = (updatedRestaurant) => {
    setSearchResults(prevResults => 
      prevResults.map(restaurant => 
        restaurant.place_id === updatedRestaurant.place_id 
          ? updatedRestaurant 
          : restaurant
      )
    );
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-start px-6 py-10 bg-transparent">
      
      {/* 🔹 Top Right Buttons (fixed) */}
      <div className="absolute top-6 right-6 flex gap-3 z-10">
        <button
          onClick={onOpenChat}
          className="btn btn-ghost shadow-lg"
        >
          💬 Chat
        </button>
        {isAdmin && (
          <button
            onClick={onManageUsers}
            className="btn btn-ghost shadow-lg"
          >
            Manage Users
          </button>
        )}
        <button
          onClick={onSignOut}
          className="btn btn-secondary shadow-lg"
        >
          Sign Out
        </button>
      </div>

      {/* 🔹 Centered Heading */}
      <div className="flex flex-col items-center text-center max-w-2xl fade-up mt-10">
        <h1 className="header-xl tracking-tight mb-3">
          Discover Amazing Restaurants
        </h1>
        <p className="text-slate-600 text-lg mb-10 leading-relaxed">
          Search for restaurants in your favorite city — explore, rate, and enjoy
          your culinary journey 🍽️
        </p>
      </div>

      {/* 🔹 Search Bar */}
      <form
        onSubmit={handleSearch}
        className="flex flex-col sm:flex-row items-center justify-center w-full max-w-2xl gap-3 fade-up"
      >
        <input
          id="searchQuery"
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(sanitizeInput(e.target.value, 200))}
          placeholder="Enter city name (e.g., Toronto, Paris, Tokyo)"
          className="input w-full"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !searchQuery.trim()}
          className="btn btn-primary w-full sm:w-auto"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </form>

      {/* 🔹 Error Message */}
      {error && (
        <div className="glass p-3 rounded-lg border mt-4 border-red-200/70 text-red-700 text-sm fade-up">
          {error}
        </div>
      )}

      {/* 🔹 Suggested Cities (shown before first search) */}
      {!hasSearched && (
        <div className="mt-14 text-center fade-up">
          <h3 className="text-lg font-semibold text-slate-700 mb-4">
            Try these popular cities:
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            {["New York", "Paris", "Tokyo", "London"].map((city) => (
              <button
                key={city}
                onClick={() => setSearchQuery(city)}
                className="btn btn-ghost text-slate-800 font-semibold shadow-sm hover:-translate-y-0.5 transition-transform"
              >
                {city}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 🔹 Results Grid */}
      {searchResults.length > 0 && (
        <div className="w-full max-w-6xl mt-16 fade-up">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 justify-center">
            {searchResults.map((restaurant, idx) => (
              <div
                key={restaurant.place_id || idx}
                className="mx-auto max-w-[350px] w-full transform hover:scale-[1.02] transition-transform duration-300"
              >
                <ErrorBoundary>
                  <RestaurantFlipCard
                    restaurant={restaurant}
                    isSearchResult={true}
                    onRatingUpdate={() => {}}
                    onRestaurantDataUpdate={handleRestaurantDataUpdate}
                  />
                </ErrorBoundary>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 🔹 No Results */}
      {searchResults.length === 0 && hasSearched && !isLoading && (
        <div className="mt-20 text-center fade-up max-w-2xl">
          <h3 className="text-2xl font-bold text-slate-900 mb-2">
            No restaurants found
          </h3>
          <p className="text-slate-600 mb-6">
            We couldn't find any restaurants in{" "}
            <span className="font-semibold text-blue-700">{searchQuery}</span>.
            Try another city.
          </p>
          <button
            onClick={() => {
              setSearchQuery("");
              setHasSearched(false);
            }}
            className="btn btn-primary"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}

export default RestaurantSearch;