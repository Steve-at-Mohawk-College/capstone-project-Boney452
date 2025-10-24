import { useState } from "react";
import RestaurantRating from "./RestaurantRating";

/* Inline SVG icons (no emoji) */
const Star = ({ filled = false, className = "" }) => (
  <svg viewBox="0 0 20 20" aria-hidden="true"
       className={`${className} ${filled ? "fill-yellow-400 stroke-yellow-400" : "fill-transparent stroke-slate-300"}`}
       width="20" height="20" strokeWidth="1.5">
    <path d="M10 2.5l2.47 4.98 5.5.8-3.98 3.88.94 5.48L10 15.9 5.07 17.64l.94-5.48L2.02 8.28l5.5-.8L10 2.5z"/>
  </svg>
);

const Dollar = ({ className = "" }) => (
  <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18"
       className={`${className} stroke-emerald-600`} strokeWidth="1.8" fill="none">
    <path d="M12 2v20M16.5 7.5c0-1.9-1.9-3.5-4.5-3.5S7.5 5.6 7.5 7.5 9.4 11 12 11s4.5 1.6 4.5 3.5S14.6 18 12 18s-4.5-1.6-4.5-3.5"/>
  </svg>
);

/* Helpers */
const renderStars = (value) => {
  try {
    const v = Math.round(Number(value) || 0);
    return (
      <div className="star-row">
        {[1,2,3,4,5].map(i => <Star key={i} filled={i <= v} />)}
      </div>
    );
  } catch (error) {
    console.error("Error rendering stars:", error);
    return <div className="star-row">Error</div>;
  }
};

const PriceBadge = ({ level = 0 }) => {
  try {
    if (!level || typeof level !== 'number' || level <= 0) return null;
    return (
      <span className="badge badge-mint">
        <span className="flex items-center gap-1">
          {Array.from({ length: Math.floor(level) }).map((_,i) => <Dollar key={i} />)}
        </span>
      </span>
    );
  } catch (error) {
    console.error("Error rendering price badge:", error);
    return null;
  }
};

function RestaurantFlipCard({ restaurant, isSearchResult = false, onRatingUpdate, onRestaurantDataUpdate }) {
  const [isFlipped, setIsFlipped] = useState(false);

  // Safety check - if no restaurant data, return null
  if (!restaurant) {
    return null;
  }

  const handleCardClick = (e) => {
    // Don't flip if interacting with controls
    if (e.target.closest("button, form, textarea, input, select, label")) return;
    setIsFlipped(!isFlipped);
  };

  const handleRatingDataUpdate = (ratingData) => {
    // Update the restaurant data with new rating information
    if (onRestaurantDataUpdate) {
      onRestaurantDataUpdate({
        ...restaurant,
        ...ratingData
      });
    }
  };

  try {
    // Determine if this is from database or Google API
    const isFromDatabase = restaurant?.from_database === true;
  
  const name = isFromDatabase ? (restaurant?.name || "Unknown Restaurant") : (isSearchResult ? (restaurant?.name || "Unknown Restaurant") : (restaurant?.Name || "Unknown Restaurant"));
  
  // Google rating (from search results or database)
  const googleRating = restaurant?.rating ?? null;
  
  // Database rating (from our users)
  const databaseRating = restaurant?.AverageRating ?? null;
  
  const googleRatingText = googleRating && typeof googleRating === 'number' ? googleRating.toFixed(1) : "N/A";
  const databaseRatingText = databaseRating && typeof databaseRating === 'number' ? databaseRating.toFixed(1) : "N/A";
  const totalRatings = restaurant?.TotalRatings ?? 0;
  
  const priceLevel = isFromDatabase ? (restaurant?.price_level || 0) : (isSearchResult ? (restaurant?.price_level || 0) : 0);
  const address = isFromDatabase ? (restaurant?.formatted_address || "Address not available") : (isSearchResult ? (restaurant?.formatted_address || "Address not available") : (restaurant?.Location || "Address not available"));
  const ratingMessage = isFromDatabase ? null : (isSearchResult ? null : restaurant?.RatingMessage);

  return (
    <div className="flip-card-container fade-up">
      <div
        className={`flip-card ${isFlipped ? "flipped" : ""}`}
        onClick={handleCardClick}
      >
        {/* FRONT */}
        <div
          className="flip-face flip-front"
          style={{
            '--bg-image': isSearchResult && restaurant?.photo_url ? `url(${restaurant.photo_url})` : 'none'
          }}
        >
          <div className="card-content">
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <h4 className="restaurant-name">{name}</h4>

                <div className="meta-row mt-3">
                  {/* Google Rating */}
                  {googleRating && (
                    <span className="badge badge-gold">
                      <span className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-600">Google:</span>
                        {renderStars(googleRating)}
                        <span className="font-extrabold">{googleRatingText}</span>
                      </span>
                    </span>
                  )}

                  {/* Database Rating */}
                  {databaseRating && (
                    <span className="badge badge-mint">
                      <span className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-600">Users:</span>
                        {renderStars(databaseRating)}
                        <span className="font-extrabold">{databaseRatingText}</span>
                        {totalRatings > 0 && (
                          <span className="text-xs text-slate-500">({totalRatings})</span>
                        )}
                      </span>
                    </span>
                  )}

                  {/* No ratings message */}
                  {!googleRating && !databaseRating && (
                    <span className="badge">
                      <span className="text-slate-600 text-sm">No ratings yet</span>
                    </span>
                  )}

                  {/* Price badge */}
                  {(isFromDatabase || isSearchResult) && <PriceBadge level={priceLevel} />}

                  {/* Rating message for DB items */}
                  {!isFromDatabase && !isSearchResult && ratingMessage && (
                    <span className="badge">
                      <span className="text-slate-700">{ratingMessage}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Details */}
            <div className="flex-1 mt-4 flex flex-col gap-3 min-h-0">
                      {/* Cuisine tags */}
                      {isFromDatabase ? (
                        restaurant?.types && Array.isArray(restaurant.types) && restaurant.types.length > 0 && (
                          <div className="cuisine-tags">
                            {restaurant.types.slice(0,3).map((type, idx) => (
                              <span key={idx} className="cuisine-tag">
                                {String(type || "").replace(/_/g," ").toUpperCase()}
                              </span>
                            ))}
                          </div>
                        )
                      ) : isSearchResult ? (
                        restaurant?.types && Array.isArray(restaurant.types) && restaurant.types.length > 0 && (
                          <div className="cuisine-tags">
                            {restaurant.types.slice(0,3).map((type, idx) => (
                              <span key={idx} className="cuisine-tag">
                                {String(type || "").replace(/_/g," ").toUpperCase()}
                              </span>
                            ))}
                          </div>
                        )
                      ) : (
                        restaurant?.["Cuisine Type"] && (
                          <div className="cuisine-tags">
                            <span className="cuisine-tag">{String(restaurant["Cuisine Type"] || "")}</span>
                          </div>
                        )
                      )}

              {/* Address */}
              {address && (
                <div className="address">
                  <div className="text-sm text-slate-500 font-semibold mb-1">Address</div>
                  <div className="text-slate-700">{address}</div>
                </div>
              )}

              {/* User's rating on front face */}
              {(isFromDatabase || isSearchResult) && restaurant?.user_rating && (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-blue-700">Your Rating:</span>
                  <div className="star-row">
                    {renderStars(restaurant?.user_rating)}
                  </div>
                </div>
              )}

            </div>

                    {/* Flip hint */}
                    <div className="hint">Click to {(isFromDatabase || isSearchResult) && restaurant?.user_review ? "update your review" : "rate & review"}</div>
          </div>
        </div>

        {/* BACK */}
        <div
          className="flip-face flip-back"
          style={{
            '--bg-image': isSearchResult && restaurant?.photo_url ? `url(${restaurant.photo_url})` : 'none'
          }}
        >
          <div className="card-content">
            {/* Back header */}
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-[1.05rem] font-extrabold text-slate-900 tracking-tight">Rate &amp; Review</h4>
              {/* optional small brand badge */}
              <span className="badge">Flavor&nbsp;Quest</span>
            </div>

            {/* Name back */}
            <div className="glass p-2 rounded-lg border border-slate-200/70">
              <p className="text-sm font-semibold text-slate-800 text-center truncate">{name}</p>
            </div>

            {/* Rating form */}
            <div className="rating-scroll mt-2">
                      <RestaurantRating
                        restaurantId={null}
                        restaurantName={name}
                        onRatingUpdate={onRatingUpdate}
                        isCompact={true}
                        searchResultData={restaurant}
                        onRatingDataUpdate={handleRatingDataUpdate}
                      />
            </div>

            {/* User's review display on back */}
            {(isFromDatabase || isSearchResult) && restaurant?.user_review && String(restaurant.user_review).trim() && (
              <div className="glass p-3 rounded-xl mt-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-700">Your Review</span>
                  <div className="star-row">
                    {renderStars(restaurant?.user_rating)}
                  </div>
                </div>
                <p className="text-sm text-slate-700/90 italic">{String(restaurant.user_review || "")}</p>
              </div>
            )}

            {/* Back hint */}
            <div className="hint">Click to go back</div>
          </div>
        </div>
      </div>
    </div>
  );
  } catch (error) {
    console.error("Error in RestaurantFlipCard:", error);
    return (
      <div className="flip-card-container fade-up">
        <div className="glass p-4 rounded-xl border border-red-200/70">
          <h4 className="text-red-700 font-semibold mb-2">Error Loading Restaurant</h4>
          <p className="text-red-600 text-sm">Unable to display restaurant information</p>
        </div>
      </div>
    );
  }
}

export default RestaurantFlipCard;