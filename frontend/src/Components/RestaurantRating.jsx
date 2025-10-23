import { useState, useEffect } from "react";
import axios from "axios";

function RestaurantRating({ restaurantId, restaurantName, onRatingUpdate, isCompact = false, searchResultData = null }) {
  const [rating, setRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [myRating, setMyRating] = useState(null);
  const [restaurantRatings, setRestaurantRatings] = useState(null);
  const [showRatingForm, setShowRatingForm] = useState(false);
  const [error, setError] = useState("");

  // Get user's token from localStorage
  const getToken = () => {
    return localStorage.getItem("token");
  };

  // Initialize rating and review from search result data
  useEffect(() => {
    if (searchResultData && searchResultData.user_review) {
      setRating(searchResultData.user_rating || 0);
      setReviewText(searchResultData.user_review || "");
    }
  }, [searchResultData]);

  // Load restaurant ratings and user's rating
  useEffect(() => {
    if (restaurantId) {
      loadRestaurantRatings();
      loadMyRating();
    }
  }, [restaurantId]);

  const loadRestaurantRatings = async () => {
    try {
      const response = await axios.get(`http://localhost:5002/restaurants/${restaurantId}/ratings`);
      setRestaurantRatings(response.data);
    } catch (err) {
      console.error("Failed to load restaurant ratings:", err);
    }
  };

  const loadMyRating = async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await axios.get(`http://localhost:5002/restaurants/${restaurantId}/my-rating`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMyRating(response.data);
      setRating(response.data.rating);
      setReviewText(response.data.review_text || "");
    } catch (err) {
      if (err.response?.status !== 404) {
        console.error("Failed to load my rating:", err);
      }
    }
  };

  const handleSubmitRating = async (e) => {
    e.preventDefault();
    const token = getToken();
    
    if (!token) {
      setError("Please login to rate restaurants");
      return;
    }

    if (rating < 1 || rating > 5) {
      setError("Please select a rating between 1 and 5");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      // If no restaurantId, we need to find the restaurant in our database first
      if (!restaurantId && searchResultData) {
        // This is a search result, try to find it in our database first
        try {
          console.log("Search result data:", searchResultData);
          console.log("Place ID being searched:", searchResultData.place_id);
          
          // First, try to find the restaurant by place_id in our database
          const searchResponse = await axios.get(`http://localhost:5002/restaurants/search?place_id=${searchResultData.place_id}`);
          
          if (searchResponse.data && searchResponse.data.length > 0) {
            // Restaurant found in database, use its ID
            restaurantId = searchResponse.data[0].ResturantsId;
            console.log("Found restaurant in database with ID:", restaurantId);
          } else {
            // Restaurant not found, add it to database
            console.log("Restaurant not found in database, adding it...");
            const addResponse = await axios.post("http://localhost:5002/add-google-place", {
              place_id: searchResultData.place_id
            });
            
            if (addResponse.data && (addResponse.data.restaurant_id || addResponse.data.restaurant?.ResturantsId)) {
              restaurantId = addResponse.data.restaurant_id || addResponse.data.restaurant.ResturantsId;
              console.log("Added restaurant to database with ID:", restaurantId);
            } else {
              setError("Failed to add restaurant to database. Please try again.");
              setIsSubmitting(false);
              return;
            }
          }
        } catch (searchError) {
          console.error("Error searching/adding restaurant:", searchError);
          setError("Failed to find or add restaurant to database. Please try again.");
          setIsSubmitting(false);
          return;
        }
      } else if (!restaurantId) {
        setError("Restaurant not found. Please try again.");
        setIsSubmitting(false);
        return;
      }

      const response = await axios.post(
        `http://localhost:5002/restaurants/${restaurantId}/rate`,
        {
          rating: rating,
          review_text: reviewText
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      // Reload ratings after successful submission
      await loadRestaurantRatings();
      await loadMyRating();
      
      setShowRatingForm(false);
      if (onRatingUpdate) {
        onRatingUpdate();
      }
    } catch (err) {
      setError("Failed to submit rating. Please try again.");
      console.error("Rating submission error:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteRating = async () => {
    const token = getToken();
    if (!token) return;

    try {
      await axios.delete(`http://localhost:5002/restaurants/${restaurantId}/rate`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      // Reload ratings after successful deletion
      await loadRestaurantRatings();
      setMyRating(null);
      setRating(0);
      setReviewText("");
      setShowRatingForm(false);
      
      if (onRatingUpdate) {
        onRatingUpdate();
      }
    } catch (err) {
      setError("Failed to delete rating. Please try again.");
      console.error("Rating deletion error:", err);
    }
  };

  const renderStars = (rating, interactive = false, onStarClick = null, compact = false) => {
    return (
      <div className="flex space-x-2 justify-center" onClick={(e) => e.stopPropagation()}>
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type={interactive ? "button" : undefined}
            onClick={interactive ? (e) => {
              e.stopPropagation();
              onStarClick(star);
            } : undefined}
            className={`${compact ? 'text-xl' : 'text-3xl'} transition-all duration-300 ${
              star <= rating
                ? "text-yellow-400 drop-shadow-lg"
                : "text-gray-300"
            } ${interactive ? "hover:text-yellow-300 hover:scale-110 cursor-pointer transform" : ""}`}
            disabled={!interactive}
          >
            ★
          </button>
        ))}
      </div>
    );
  };

  // If no restaurantId (search results), show rating form
  if (!restaurantId && searchResultData) {
    return (
      <div className={`${isCompact ? 'p-2' : 'bg-white p-4 rounded-lg shadow-md'}`}>
        {!isCompact && <h3 className="text-lg font-semibold mb-3">
          {searchResultData.user_review ? "Edit Your Review" : "Rate This Restaurant"}
        </h3>}
        
        {/* Show message only if user hasn't rated yet */}
        {!searchResultData.user_review && (
          <div className="text-center mb-4">
            <p className="text-sm text-gray-600 mb-2">
              Be the first to rate this restaurant!
            </p>
          </div>
        )}

        {/* Rating Form */}
        {getToken() && (
          <div className="mb-4">
            {!showRatingForm ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowRatingForm(true);
                }}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-lg hover:from-blue-600 hover:to-indigo-700 w-full font-semibold shadow-lg transition-all duration-300 transform hover:scale-105"
              >
                {searchResultData.user_review ? "Edit Your Review" : "Rate This Restaurant"}
              </button>
            ) : (
              <form onSubmit={handleSubmitRating} className="space-y-4" onClick={(e) => e.stopPropagation()}>
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                  <label className="block text-sm font-semibold text-yellow-800 mb-3">Your Rating:</label>
                  {renderStars(rating, true, setRating, isCompact)}
                </div>
                
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Review (Optional):</label>
                  <textarea
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full p-3 border-2 border-slate-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-300"
                    rows="3"
                    placeholder="Share your experience..."
                  />
                </div>
                
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
                    {error}
                  </div>
                )}
                
                <div className="flex space-x-3">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-gradient-to-r from-green-500 to-emerald-600 text-white px-6 py-3 rounded-lg hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 flex-1 font-semibold shadow-lg transition-all duration-300 transform hover:scale-105"
                  >
                    {isSubmitting ? "Submitting..." : "Submit Rating"}
                  </button>
                  
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowRatingForm(false);
                    }}
                    className="bg-gradient-to-r from-gray-500 to-slate-600 text-white px-6 py-3 rounded-lg hover:from-gray-600 hover:to-slate-700 font-semibold shadow-lg transition-all duration-300"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {!getToken() && (
          <p className="text-sm text-gray-500 mt-2 text-center">
            Please login to rate this restaurant
          </p>
        )}
      </div>
    );
  }

  if (!restaurantRatings) {
    return <div className="text-gray-500 text-sm">Loading ratings...</div>;
  }

  return (
    <div className={`${isCompact ? 'p-2' : 'bg-white p-4 rounded-lg shadow-md'}`}>
      {!isCompact && <h3 className="text-lg font-semibold mb-3">Restaurant Ratings</h3>}
      
      {/* Rating Summary */}
      <div className={`${isCompact ? 'mb-2 p-2' : 'mb-6 p-4'} bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg border border-yellow-200`}>
        <div className="text-center">
          <div className={`${isCompact ? 'mb-1' : 'mb-3'}`}>
            {renderStars(Math.round(restaurantRatings.average_rating || 0), false, null, isCompact)}
          </div>
          <div className="space-y-1">
            <p className={`${isCompact ? 'text-sm' : 'text-lg'} font-bold text-slate-800`}>
              {restaurantRatings.average_rating ? `${restaurantRatings.average_rating.toFixed(1)}/5.0` : "No Rating"}
            </p>
            <p className={`${isCompact ? 'text-xs' : 'text-sm'} text-slate-600 font-medium`}>
              {restaurantRatings.user_rating_message}
            </p>
          </div>
        </div>
      </div>

      {/* Rating Form */}
      {getToken() && (
        <div className={`${isCompact ? 'mb-2' : 'mb-4'}`}>
          {!showRatingForm ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowRatingForm(true);
              }}
              className={`bg-gradient-to-r from-blue-500 to-indigo-600 text-white ${isCompact ? 'px-3 py-2 text-sm' : 'px-6 py-3'} rounded-lg hover:from-blue-600 hover:to-indigo-700 font-semibold shadow-lg transition-all duration-300 transform hover:scale-105`}
            >
              {myRating ? "Update My Rating" : "Rate This Restaurant"}
            </button>
          ) : (
            <form onSubmit={handleSubmitRating} className={`${isCompact ? 'space-y-2' : 'space-y-4'}`} onClick={(e) => e.stopPropagation()}>
              <div className={`bg-yellow-50 ${isCompact ? 'p-2' : 'p-4'} rounded-lg border border-yellow-200`}>
                <label className={`block ${isCompact ? 'text-xs' : 'text-sm'} font-semibold text-yellow-800 ${isCompact ? 'mb-1' : 'mb-3'}`}>Your Rating:</label>
                {renderStars(rating, true, setRating, isCompact)}
              </div>
              
              <div>
                <label className={`block ${isCompact ? 'text-xs' : 'text-sm'} font-semibold text-slate-700 ${isCompact ? 'mb-1' : 'mb-2'}`}>Review (Optional):</label>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                  className={`w-full ${isCompact ? 'p-2' : 'p-3'} border-2 border-slate-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-300`}
                  rows={isCompact ? "2" : "3"}
                  placeholder="Share your experience..."
                />
              </div>
              
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
                  {error}
                </div>
              )}
              
              <div className="flex space-x-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  onClick={(e) => e.stopPropagation()}
                  className={`bg-gradient-to-r from-green-500 to-emerald-600 text-white ${isCompact ? 'px-2 py-1 text-xs' : 'px-4 py-2'} rounded-lg hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 font-semibold shadow-lg transition-all duration-300 flex-1`}
                >
                  {isSubmitting ? "Submitting..." : "Submit Rating"}
                </button>
                
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowRatingForm(false);
                  }}
                  className={`bg-gradient-to-r from-gray-500 to-slate-600 text-white ${isCompact ? 'px-2 py-1 text-xs' : 'px-4 py-2'} rounded-lg hover:from-gray-600 hover:to-slate-700 font-semibold shadow-lg transition-all duration-300`}
                >
                  Cancel
                </button>
                
                {myRating && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteRating();
                    }}
                    className={`bg-gradient-to-r from-red-500 to-pink-600 text-white ${isCompact ? 'px-2 py-1 text-xs' : 'px-4 py-2'} rounded-lg hover:from-red-600 hover:to-pink-700 font-semibold shadow-lg transition-all duration-300`}
                  >
                    Delete
                  </button>
                )}
              </div>
            </form>
          )}
        </div>
      )}

      {/* User Reviews */}
      {restaurantRatings.ratings && restaurantRatings.ratings.length > 0 && (
        <div>
          <h4 className="font-medium mb-2">User Reviews:</h4>
          <div className="space-y-3 max-h-60 overflow-y-auto">
            {restaurantRatings.ratings.map((rating, index) => (
              <div key={index} className="border-l-4 border-blue-500 pl-3">
                <div className="flex items-center space-x-2 mb-1">
                  {renderStars(rating.rating, false, null, isCompact)}
                  <span className="text-sm font-medium">{rating.username}</span>
                  <span className="text-xs text-gray-500">
                    {new Date(rating.created_at).toLocaleDateString()}
                  </span>
                </div>
                {rating.review_text && (
                  <p className="text-sm text-gray-700">{rating.review_text}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!getToken() && (
        <p className="text-sm text-gray-500 mt-2">
          Please login to rate this restaurant
        </p>
      )}
    </div>
  );
}

export default RestaurantRating;
