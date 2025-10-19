import { useState } from "react";
import RestaurantRating from "./RestaurantRating";

function RestaurantFlipCard({ restaurant, isSearchResult = false, onRatingUpdate }) {
  const [isFlipped, setIsFlipped] = useState(false);

  const handleCardClick = () => {
    setIsFlipped(!isFlipped);
  };

  const renderStars = (rating) => {
    if (!rating) return "N/A";
    return "⭐".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
  };

  const renderPriceLevel = (priceLevel) => {
    if (!priceLevel) return null;
    return "💰".repeat(priceLevel);
  };

  return (
    <div className="flip-card-container">
      <div 
        className={`flip-card ${isFlipped ? "flipped" : ""}`}
        onClick={handleCardClick}
      >
        {/* Front of the card - Restaurant Info */}
        <div 
          className="flip-card-front"
          style={{
            backgroundImage: isSearchResult && restaurant.photo_url ? `url(${restaurant.photo_url})` : 'none',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat'
          }}
        >
          {/* Background overlay for text readability */}
          {isSearchResult && restaurant.photo_url && (
            <div className="card-overlay" />
          )}
          
          {/* Content */}
          <div className="card-content">
            {/* Restaurant Header */}
            <div className="restaurant-header">
              <div className="restaurant-info">
                <h4 className="restaurant-name">
                  {isSearchResult ? restaurant.name : restaurant.Name}
                </h4>
                <div className="rating-price-container">
                  <div className="rating-badge">
                    <span className="rating-text">
                      {isSearchResult ? 
                        (restaurant.rating ? `${restaurant.rating.toFixed(1)}` : "N/A") :
                        (restaurant.AverageRating ? `${restaurant.AverageRating.toFixed(1)}` : "N/A")
                      }
                    </span>
                  </div>
                  {isSearchResult && restaurant.price_level && (
                    <div className="price-badge">
                      <span className="price-text">
                        {renderPriceLevel(restaurant.price_level)}
                      </span>
                    </div>
                  )}
                  {!isSearchResult && (
                    <div className="rating-message-badge">
                      <span className="rating-message-text">
                        {restaurant.RatingMessage}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="restaurant-avatar">
                {(isSearchResult ? restaurant.name : restaurant.Name).charAt(0)}
              </div>
            </div>

            {/* Restaurant Details */}
            <div className="restaurant-details">
              {/* Cuisine Type */}
              {isSearchResult ? (
                restaurant.types && restaurant.types.length > 0 && (
                  <div className="cuisine-tags">
                    {restaurant.types.slice(0, 3).map((type, idx) => (
                      <span key={idx} className="cuisine-tag">
                        {type.replace(/_/g, " ").toUpperCase()}
                      </span>
                    ))}
                  </div>
                )
              ) : (
                <div className="cuisine-tags">
                  <span className="cuisine-tag">
                    {restaurant["Cuisine Type"]}
                  </span>
                </div>
              )}

              {/* Address */}
              <div className="address-container">
                <div className="address-content">
                  <span className="address-label">Address:</span>
                  <p className="address-text">
                    {isSearchResult ? restaurant.formatted_address : restaurant.Location}
                  </p>
                </div>
              </div>

              {/* Rating Message for Database Restaurants */}
              {!isSearchResult && (
                <div className="rating-message-container">
                  <p className="rating-message-text">
                    {restaurant.RatingMessage}
                  </p>
                </div>
              )}
            </div>

            {/* Click to Rate Hint */}
            <div className="click-hint">
              <p className="hint-text">Click to rate and review</p>
            </div>
          </div>
        </div>

        {/* Back of the card - Rating UI */}
        <div 
          className="flip-card-back"
          style={{
            backgroundImage: isSearchResult && restaurant.photo_url ? `url(${restaurant.photo_url})` : 'none',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat'
          }}
        >
          {/* Background overlay for text readability */}
          {isSearchResult && restaurant.photo_url && (
            <div className="card-overlay" />
          )}
          
          {/* Content */}
          <div className="card-content">
            {/* Back Header */}
            <div className="back-header">
              <h4 className="back-title">Rate & Review</h4>
              <div className="back-avatar">R</div>
            </div>

            {/* Restaurant Name on Back */}
            <div className="restaurant-name-back">
              <p className="restaurant-name-text">
                {isSearchResult ? restaurant.name : restaurant.Name}
              </p>
            </div>

            {/* Rating Component */}
            <div className="rating-component-container">
              <RestaurantRating 
                restaurantId={isSearchResult ? null : restaurant.ResturantsId} 
                restaurantName={isSearchResult ? restaurant.name : restaurant.Name}
                onRatingUpdate={onRatingUpdate}
                isCompact={true}
                searchResultData={isSearchResult ? restaurant : null}
              />
            </div>

            {/* Click to Go Back Hint */}
            <div className="back-hint">
              <p className="hint-text">Click to go back</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RestaurantFlipCard;