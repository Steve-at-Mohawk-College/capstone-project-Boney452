import { useState, useEffect } from "react";
import axios from "axios";
import { sanitizeInput, validateRating, sanitizeRestaurantData, csrfManager, containsInappropriateContent } from "../utils/security";
import { API_BASE_URL } from "../config";
import { tokenStorage } from "../utils/tokenStorage";

function RestaurantRating({ restaurantId, restaurantName, onRatingUpdate, isCompact = false, searchResultData = null, onRatingDataUpdate = null }) {
  const [rating, setRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [myRating, setMyRating] = useState(null);
  const [restaurantRatings, setRestaurantRatings] = useState(null);
  const [showRatingForm, setShowRatingForm] = useState(false);
  const [error, setError] = useState("");

  // Safety check - if no restaurant name, return null
  if (!restaurantName) {
    return null;
  }

  // Get user's token from storage
  const getToken = () => tokenStorage.get();

  // Initialize rating and review from search result data
  useEffect(() => {
    if (searchResultData && searchResultData.user_review) {
      const sanitizedData = sanitizeRestaurantData(searchResultData);
      setRating(sanitizedData.user_rating || 0);
      setReviewText(sanitizedData.user_review || "");
    }
  }, [searchResultData]);

  // Load restaurant ratings and user's rating
  useEffect(() => {
    // Always use search result data if available (which should be the case for all restaurants now)
    if (searchResultData) {
      // Debug: Log the search result data to see what we're working with
      console.log("RestaurantRating useEffect - searchResultData:", searchResultData);
      console.log("RestaurantRating useEffect - user_review:", searchResultData.user_review);
      console.log("RestaurantRating useEffect - TotalRatings:", searchResultData.TotalRatings);
      
      setRestaurantRatings({
        average_rating: searchResultData.AverageRating || null,
        ratings: [],
        restaurant_id: searchResultData.ResturantsId || null,
        restaurant_name: restaurantName,
        total_ratings: searchResultData.TotalRatings || 0,
        user_rating_message: (() => {
          const hasRatings = (searchResultData.TotalRatings || 0) > 0;
          const hasUserReview = !!searchResultData.user_review;
          const shouldShowMessage = !hasRatings && !hasUserReview;
          const message = shouldShowMessage ? "Have not been rated by users" : null;
          console.log("RestaurantRating useEffect - hasRatings:", hasRatings, "hasUserReview:", hasUserReview, "shouldShowMessage:", shouldShowMessage, "message:", message);
          return message;
        })()
      });
      
      // Set user's rating if available
      if (searchResultData.user_rating) {
        setMyRating({
          rating: searchResultData.user_rating,
          review_text: searchResultData.user_review
        });
        setRating(searchResultData.user_rating);
        setReviewText(searchResultData.user_review || "");
      }
    } else if (restaurantId) {
      // Fallback to API calls only if no search data available (shouldn't happen in normal flow)
      console.log("WARNING: Making API calls - this should not happen!");
      // loadRestaurantRatings();
      // loadMyRating();
    } else {
      // For cases without any data, set empty ratings
      setRestaurantRatings({
        average_rating: null,
        ratings: [],
        restaurant_id: null,
        restaurant_name: restaurantName,
        total_ratings: 0,
        user_rating_message: searchResultData?.user_review ? null : "Have not been rated by users"
      });
    }
  }, [restaurantId, searchResultData]);

  const loadRestaurantRatings = async () => {
    // DISABLED: This should not be called anymore
    return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/restaurants/${restaurantId}/ratings`);
      setRestaurantRatings(response.data);
    } catch (err) {
      console.error("Failed to load restaurant ratings:", err);
      // Set default empty ratings to prevent loading state
      setRestaurantRatings({
        average_rating: null,
        ratings: [],
        restaurant_id: restaurantId,
        restaurant_name: restaurantName,
        total_ratings: 0,
        user_rating_message: searchResultData?.user_review ? null : "Have not been rated by users"
      });
    }
  };

  const loadMyRating = async () => {
    // DISABLED: This should not be called anymore
    return;
    
    const token = getToken();
    if (!token) return;

    try {
      const response = await axios.get(`${API_BASE_URL}/restaurants/${restaurantId}/my-rating`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data && typeof response.data === 'object') {
        setMyRating(response.data);
        setRating(response.data.rating || 0);
        setReviewText(response.data.review_text || "");
      }
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
      setError("Authentication required to rate restaurants. Please sign in to continue.");
      return;
    }

    // Validate rating
    if (!validateRating(rating)) {
      setError("Please select a rating between 1 and 5 stars.");
      return;
    }

    // Sanitize review text
    const sanitizedReviewText = sanitizeInput(reviewText, 1000);
    
    // Check for inappropriate content
    if (containsInappropriateContent(sanitizedReviewText)) {
      setError("Your review contains inappropriate content. Please revise your review and try again.");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      // Use restaurant ID from search data if available
      let targetRestaurantId = restaurantId;
      
      if (!targetRestaurantId && searchResultData) {
        // Use the restaurant ID from search data
        targetRestaurantId = searchResultData.ResturantsId;
        
        if (!targetRestaurantId) {
          setError("Restaurant information could not be found. Please try again.");
          setIsSubmitting(false);
          return;
        }
      } else if (!targetRestaurantId) {
        setError("Restaurant information could not be found. Please try again.");
        setIsSubmitting(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-CSRF-Token': csrfToken
      };
      
      const response = await axios.post(
        `${API_BASE_URL}/restaurants/${targetRestaurantId}/rate`,
        {
          rating: rating,
          review_text: sanitizedReviewText
        },
        { headers }
      );

      // Update local state immediately to show the new rating
      setMyRating({
        rating: rating,
        review_text: reviewText
      });
      
      // Update restaurant ratings to reflect the new rating
      setRestaurantRatings(prev => ({
        ...prev,
        average_rating: rating, // For now, show user's rating as average (will be updated on next search)
        total_ratings: 1, // User just added the first rating
        user_rating_message: "Rated by 1 user"
      }));
      
      setShowRatingForm(false);
      
      // Update parent component with new rating data
      if (onRatingDataUpdate) {
        onRatingDataUpdate({
          user_rating: rating,
          user_review: reviewText,
          AverageRating: rating,
          TotalRatings: 1
        });
      }
      
      if (onRatingUpdate) {
        onRatingUpdate();
      }
    } catch (err) {
      console.error("Rating submission error:", err);
      setError("Unable to submit rating. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteRating = async () => {
    const token = getToken();
    if (!token) {
      setError("Authentication required to delete ratings. Please sign in to continue.");
      return;
    }

    // Use restaurant ID from search data if available
    let targetRestaurantId = restaurantId;
    if (!targetRestaurantId && searchResultData) {
      targetRestaurantId = searchResultData.ResturantsId;
    }

    if (!targetRestaurantId) {
      setError("Restaurant not found. Please try again.");
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      const csrfToken = await csrfManager.getToken();
      
      // Use axios config format for DELETE with headers
      await axios({
        method: 'delete',
        url: `${API_BASE_URL}/restaurants/${targetRestaurantId}/rate`,
        headers: { 
          Authorization: `Bearer ${token}`,
          "X-CSRF-Token": csrfToken,
          "Content-Type": "application/json"
        }
      });

      // Update local state after successful deletion
      setMyRating(null);
      setRating(0);
      setReviewText("");
      setShowRatingForm(false);
      
      // Update restaurant ratings to reflect the deletion
      setRestaurantRatings(prev => ({
        ...prev,
        average_rating: null, // No ratings left
        total_ratings: 0, // No ratings left
        user_rating_message: "Have not been rated by users"
      }));
      
      // Update parent component with deleted rating data
      if (onRatingDataUpdate) {
        onRatingDataUpdate({
          user_rating: null,
          user_review: null,
          AverageRating: null,
          TotalRatings: 0
        });
      }
      
      if (onRatingUpdate) {
        onRatingUpdate();
      }
    } catch (err) {
      console.error("Rating deletion error:", err);
      setError(err.response?.data?.error || "Unable to delete rating. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStars = (rating, interactive = false, onStarClick = null, compact = false) => {
    return (
      <div 
        className="flex space-x-2 justify-center" 
        onClick={(e) => e.stopPropagation()}
        role={interactive ? "radiogroup" : "img"}
        aria-label={interactive ? "Rating selection" : `Rating: ${rating} out of 5 stars`}
      >
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
            aria-label={interactive ? `Rate ${star} star${star !== 1 ? 's' : ''}` : undefined}
            aria-pressed={interactive && star <= rating ? "true" : "false"}
          >
            <span className="sr-only">{star <= rating ? "Filled" : "Empty"} star</span>
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
        
        {/* Show message only if restaurant has no ratings at all */}
        {!searchResultData.user_review && (searchResultData.TotalRatings || 0) === 0 && (
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
              <div className="flex gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowRatingForm(true);
                  }}
                  className="btn btn-primary flex-1"
                >
                  {searchResultData.user_review ? "Edit Your Review" : "Rate This Restaurant"}
                </button>
                {searchResultData.user_review && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm("Are you sure you want to delete your rating and review? This action cannot be undone.")) {
                        handleDeleteRating();
                      }
                    }}
                    className="btn"
                    style={{
                      background: "linear-gradient(135deg, #EF4444, #DC2626)",
                      color: "white"
                    }}
                    title="Delete your rating and review"
                  >
                    Delete Review
                  </button>
                )}
              </div>
            ) : (
              <form onSubmit={handleSubmitRating} className="space-y-4" onClick={(e) => e.stopPropagation()}>
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                  <label className="block text-sm font-semibold text-yellow-800 mb-3">Your Rating:</label>
                  {renderStars(rating, true, setRating, isCompact)}
                </div>
                
                <div>
                  <label htmlFor="reviewText" className="block text-sm font-semibold text-slate-700 mb-2">Review (Optional):</label>
                  <textarea
                    id="reviewText"
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full p-3 sm:p-4 border-2 border-slate-200 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-300 text-base min-h-[100px]"
                    rows="3"
                    placeholder="Share your experience..."
                    aria-describedby={error ? "rating-error" : undefined}
                    aria-invalid={error ? "true" : "false"}
                  />
                </div>
                
                {error && (
                  <div 
                    id="rating-error"
                    className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium"
                    role="alert"
                    aria-live="polite"
                    aria-atomic="true"
                  >
                    {error}
                  </div>
                )}
                
                <div className="flex flex-col sm:flex-row gap-2 sm:space-x-3 sm:gap-0">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    onClick={(e) => e.stopPropagation()}
                    className="btn btn-primary flex-1 w-full sm:w-auto min-h-[44px]"
                    style={{ 
                      background: "linear-gradient(135deg, #10B981, #059669)",
                      opacity: isSubmitting ? 0.6 : 1
                    }}
                    aria-busy={isSubmitting}
                    aria-live="polite"
                  >
                    {isSubmitting ? "Submitting..." : "Submit Rating"}
                  </button>
                  
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowRatingForm(false);
                    }}
                    className="btn btn-secondary w-full sm:w-auto min-h-[44px]"
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
            {restaurantRatings.total_ratings === 0 && !searchResultData?.user_review && (
              <p className={`${isCompact ? 'text-xs' : 'text-sm'} text-slate-600 font-medium`}>
                {restaurantRatings.user_rating_message}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Rating Form */}
      {getToken() && (
        <div className={`${isCompact ? 'mb-2' : 'mb-4'}`}>
          {!showRatingForm ? (
            <div className="flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowRatingForm(true);
                }}
                className={`btn btn-primary flex-1 ${isCompact ? 'text-sm px-3 py-2' : ''}`}
              >
                {myRating ? "Update My Rating" : "Rate This Restaurant"}
              </button>
              {myRating && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("Are you sure you want to delete your rating and review? This action cannot be undone.")) {
                      handleDeleteRating();
                    }
                  }}
                  className={`btn ${isCompact ? 'text-sm px-3 py-2' : ''}`}
                  style={{
                    background: "linear-gradient(135deg, #EF4444, #DC2626)",
                    color: "white"
                  }}
                  title="Delete your rating and review"
                >
                  {isCompact ? "Delete" : "Delete Review"}
                </button>
              )}
            </div>
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
                  className={`btn btn-primary flex-1 ${isCompact ? 'text-xs px-2 py-1' : ''}`}
                  style={{ 
                    background: "linear-gradient(135deg, #10B981, #059669)",
                    opacity: isSubmitting ? 0.6 : 1
                  }}
                >
                  {isSubmitting ? "Submitting..." : "Submit Rating"}
                </button>
                
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowRatingForm(false);
                  }}
                  className={`btn btn-secondary ${isCompact ? 'text-xs px-2 py-1' : ''}`}
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
                    className={`btn ${isCompact ? 'text-xs px-2 py-1' : ''}`}
                    style={{
                      background: "linear-gradient(135deg, #EF4444, #DC2626)",
                      color: "white"
                    }}
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
            {restaurantRatings.ratings.map((ratingItem, index) => (
              <div key={index} className="border-l-4 border-blue-500 pl-3 relative">
                  <div className="flex items-center space-x-2 mb-1">
                    {renderStars(ratingItem.rating, false, null, isCompact)}
                    <span className="text-sm font-medium">{ratingItem.username}</span>
                    <span className="text-xs text-gray-500">
                      {new Date(ratingItem.created_at).toLocaleDateString()}
                    </span>
                  </div>
                {ratingItem.review_text && (
                  <p className="text-sm text-gray-700">{ratingItem.review_text}</p>
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
