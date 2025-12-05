/**
 * Main Application Component
 * 
 * This is the root component of the Flavor Quest application. It manages:
 * - Application routing and view state
 * - User authentication and session management
 * - Global application state (user info, search results, etc.)
 * - Navigation between different views (landing, login, search, profile, etc.)
 * 
 * @component
 * @module App
 * 
 * @description
 * The App component uses a view-based routing system (not React Router) to manage
 * different application states. It handles authentication token validation on mount
 * and provides callback functions for child components to update application state.
 * 
 * @state {string} currentView - Current application view/route
 *   Possible values: "landing", "login", "signup", "search", "results", "chat", "profile", "users"
 * @state {string} token - Authentication token from session storage
 * @state {Object|null} userInfo - Current user information object
 * @state {Array} searchResults - Array of restaurant search results
 * @state {string} searchQuery - Current search query string
 * @state {boolean} isLoading - Loading state for authentication check
 * 
 * @security
 * - Tokens are stored in sessionStorage (cleared on browser close)
 * - Invalid tokens are automatically cleared
 * - Authentication checks have timeout protection (3 seconds)
 * 
 * @performance
 * - Uses AbortController for request cancellation
 * - Prevents unnecessary re-renders with proper dependency arrays
 */

import { useState, useEffect } from "react";
import Login from "./Components/login";
import Signup from "./Components/signup";
import RestaurantSearch from "./Components/RestaurantSearch";
import UserManagement from "./Components/UserManagement";
import ChatSystem from "./Components/ChatSystem";
import UserProfile from "./Components/UserProfile";
import { API_BASE_URL } from "./config";
import { tokenStorage } from "./utils/tokenStorage";

function App() {
  // ============================================================================
  // State Management
  // ============================================================================
  
  /** Current application view/route */
  const [currentView, setCurrentView] = useState("landing");
  
  /** Authentication token from session storage */
  const [token, setToken] = useState(tokenStorage.get());
  
  /** Current authenticated user information */
  const [userInfo, setUserInfo] = useState(null);
  
  /** Array of restaurant search results */
  const [searchResults, setSearchResults] = useState([]);
  
  /** Current search query string */
  const [searchQuery, setSearchQuery] = useState("");
  
  /** Loading state for authentication validation */
  const [isLoading, setIsLoading] = useState(false);

  // ============================================================================
  // Authentication & User Management
  // ============================================================================

  /**
   * Validates authentication token on component mount
   * 
   * If a token exists in session storage, this effect:
   * 1. Fetches user information from the API
   * 2. Validates the token is still valid
   * 3. Redirects to search page if authenticated
   * 4. Clears invalid tokens and shows landing page
   * 
   * @effect
   * @dependencies {string} token - Authentication token
   * @dependencies {Object} userInfo - User information object
   * 
   * @security
   * - Uses AbortController with 3-second timeout to prevent hanging requests
   * - Automatically clears invalid or expired tokens
   * - Handles network errors gracefully
   */
  useEffect(() => {
    if (token && !userInfo) {
      setIsLoading(true);
      const fetchUserInfo = async () => {
        try {
          // Reduced timeout to 3 seconds for faster failure
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
          
          const response = await fetch(`${API_BASE_URL}/me`, {
            headers: {
              "Authorization": `Bearer ${token}`
            },
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            setUserInfo(data.user);
            // If we have a valid token and user info, redirect to search page
            setCurrentView("search");
          } else {
            // Token is invalid, clear it and stay on landing
            tokenStorage.remove();
            setToken("");
            setCurrentView("landing");
          }
        } catch (error) {
          // Error fetching user info (network error, timeout, etc.)
          console.error("Error fetching user info:", error);
          // Clear token and show landing page immediately
          tokenStorage.remove();
          setToken("");
          setCurrentView("landing");
        } finally {
          setIsLoading(false);
        }
      };
      fetchUserInfo();
    } else if (token && userInfo) {
      // We already have both token and user info, redirect to search
      setCurrentView("search");
      setIsLoading(false);
    } else if (!token) {
      // No token, show landing page
      setCurrentView("landing");
      setIsLoading(false);
    }
  }, [token, userInfo]);

  /**
   * Handles successful user login
   * 
   * Stores the authentication token, fetches user information (including admin status),
   * and navigates to the search page.
   * 
   * @param {string} newToken - JWT authentication token from login response
   */
  const handleLoginSuccess = async (newToken) => {
    tokenStorage.set(newToken);
    setToken(newToken);
    
    // Fetch user info to check if they're an admin
    try {
      const response = await fetch(`${API_BASE_URL}/me`, {
        headers: {
          "Authorization": `Bearer ${newToken}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setUserInfo(data.user);
      }
    } catch (error) {
      // Silently fail - user info will be fetched on next mount
    }
    
    // Navigate to search page after login
    setCurrentView("search");
  };

  /**
   * Handles successful user signup
   * 
   * Redirects user to login page after successful account creation.
   */
  const handleSignupSuccess = () => {
    setCurrentView("login");
  };

  /**
   * Handles restaurant search results
   * 
   * Stores search results and query, then navigates to results view.
   * 
   * @param {Array} results - Array of restaurant objects from search
   * @param {string} query - Search query string
   */
  const handleSearchResults = (results, query) => {
    setSearchResults(results);
    setSearchQuery(query);
    setCurrentView("results");
  };

  /**
   * Navigates back to search page
   * 
   * Used by child components to return to the main search interface.
   */
  const handleBackToSearch = () => {
    setCurrentView("search");
  };

  /**
   * Updates user information in application state
   * 
   * Called when user profile is updated to keep application state in sync.
   * 
   * @param {Object} updatedUserInfo - Updated user information object
   */
  const handleProfileUpdate = (updatedUserInfo) => {
    setUserInfo(updatedUserInfo);
  };

  /**
   * Checks if current user has admin privileges
   * 
   * @returns {boolean} True if user is authenticated and has admin role
   */
  const isAdmin = () => {
    if (!userInfo) return false;
    return userInfo.IsAdmin === true;
  };

  // ============================================================================
  // View Rendering
  // ============================================================================

  /**
   * Loading View
   * 
   * Displays while validating authentication token on mount.
   * Provides accessibility features for screen readers.
   */
  if (isLoading) {
    return (
      <div className="auth-page">
        <div className="w-full max-w-lg panel fade-up text-center">
          <h1 className="header-xl mb-6">Flavor Quest</h1>
          <div className="flex items-center justify-center" role="status" aria-live="polite">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" aria-hidden="true"></div>
            <span className="ml-3 text-slate-600">Loading...</span>
            <span className="sr-only">Loading application, please wait</span>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Landing Page View
   * 
   * First page users see when not authenticated.
   * Provides options to create account or sign in.
   */
  if (currentView === "landing") {
    return (
      <div className="auth-page">
        <div className="w-full max-w-lg panel fade-up">
          {/* Enhanced App Name Section */}
          <div className="text-center mb-12">
            <h1 className="header-xl mb-6">Flavor Quest</h1>
            <p className="text-xl font-semibold text-slate-700 mb-3">Discover Amazing Flavors</p>
            <p className="subtle">Your culinary journey starts here</p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col items-center space-y-4">
            {/* Create New Account Button */}
            <button
              onClick={() => setCurrentView("signup")}
              className="btn btn-primary text-xl py-5 px-16 font-medium"
              style={{ width: 'auto', minWidth: '440px' }}
            >
              Create New Account
            </button>

            {/* Sign In Button */}
            <button
              onClick={() => setCurrentView("login")}
              className="btn btn-secondary text-xl py-5 px-16 font-medium"
              style={{ width: 'auto', minWidth: '440px' }}
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Authentication Views (Login/Signup)
   * 
   * Conditionally renders login or signup form based on current view.
   */
  if (currentView === "login" || currentView === "signup") {
    return (
      <>
        {currentView === "login" ? (
          <Login 
            onLoginSuccess={handleLoginSuccess}
            onSwitchToSignup={() => setCurrentView("signup")}
            onBackToLanding={() => setCurrentView("landing")}
          />
        ) : (
          <Signup 
            onSignupSuccess={handleSignupSuccess}
            onSwitchToLogin={() => setCurrentView("login")}
            onBackToLanding={() => setCurrentView("landing")}
          />
        )}
      </>
    );
  }

  /**
   * Search Page View
   * 
   * Main application interface after authentication.
   * Allows users to search for restaurants and access other features.
   */
  if (currentView === "search") {
    return (
      <RestaurantSearch
        userInfo={userInfo}
        onSignOut={() => {
          tokenStorage.remove();
          setToken("");
          setCurrentView("landing");
          setUserInfo(null);
        }}
        onManageUsers={() => setCurrentView("users")}
        onOpenChat={() => setCurrentView("chat")}
        onOpenProfile={() => setCurrentView("profile")}
        isAdmin={isAdmin()}
      />
    );
  }

  /**
   * Search Results View
   * 
   * Displays restaurant search results with navigation options.
   * Shows search query and provides access to chat and user management.
   */
  if (currentView === "results") {
    return (
      <div className="dashboard-page w-full">
        {/* Header Bar - Back button far left */}
        <div className="bg-white border-b border-gray-200 mb-4 sm:mb-6">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4">
            <div className="flex items-center justify-between gap-2">
              <button 
                onClick={handleBackToSearch}
                className="btn btn-secondary text-xs sm:text-sm px-3 sm:px-4 py-2"
              >
                ← Back
              </button>
              <div className="flex-1"></div>
            </div>
          </div>
        </div>
        
        {/* Page Content */}
        <div className="w-full max-w-6xl mx-auto px-4 sm:px-6">
          <h1 className="header-xl fade-up mb-6">Search Results</h1>
          <div className="flex items-center justify-end gap-3 mb-6">
            <button 
              onClick={() => setCurrentView("chat")} 
              className="btn btn-ghost"
            >
              💬 Chat
            </button>
            {isAdmin() && (
              <button 
                onClick={() => setCurrentView("users")} 
                className="btn btn-ghost"
              >
                Manage Users
              </button>
            )}
            <button 
              onClick={() => {
                tokenStorage.remove();
                setToken("");
                setCurrentView("landing");
                setUserInfo(null);
              }} 
              className="btn btn-secondary"
            >
              Sign Out
            </button>
          </div>

          {/* Search query display */}
          <div className="w-full max-w-6xl mx-auto panel fade-up">
          <div className="text-center">
            <h2 className="text-xl font-bold text-slate-900 mb-2">
              Restaurants in <span className="text-blue-700">{searchQuery}</span>
            </h2>
            <p className="text-slate-600">Discover amazing dining experiences</p>
          </div>
        </div>

          {/* Restaurant results */}
          <div className="w-full max-w-6xl mx-auto mt-8 fade-up">
            <RestaurantSearch 
              userInfo={userInfo}
              onSignOut={() => {
                tokenStorage.remove();
                setToken("");
                setCurrentView("landing");
                setUserInfo(null);
              }}
              initialQuery={searchQuery}
              onSearchResults={handleSearchResults}
            />
          </div>
        </div>
      </div>
    );
  }

  /**
   * User Management View (Admin Only)
   * 
   * Administrative interface for managing user accounts.
   * Only accessible to users with admin privileges.
   * 
   * @security Requires admin authentication check
   */
  if (currentView === "users" && isAdmin()) {
    return (
      <div className="w-full">
        <UserManagement 
          onSignOut={() => {
            tokenStorage.remove();
            setToken("");
            setCurrentView("landing");
            setUserInfo(null);
          }}
          onBackToSearch={() => setCurrentView("search")}
        />
      </div>
    );
  }

  /**
   * Chat System View
   * 
   * Group-based chat interface for restaurant discussions.
   * Allows users to create, join, and participate in chat groups.
   */
  if (currentView === "chat") {
    return (
      <ChatSystem
        userInfo={userInfo}
        onSignOut={() => {
          tokenStorage.remove();
          setToken("");
          setCurrentView("landing");
          setUserInfo(null);
        }}
        onBackToSearch={() => setCurrentView("search")}
      />
    );
  }

  /**
   * User Profile View
   * 
   * User account management interface.
   * Allows users to update username, change password, and delete account.
   */
  if (currentView === "profile") {
    return (
      <UserProfile
        userInfo={userInfo}
        onSignOut={() => {
          tokenStorage.remove();
          setToken("");
          setCurrentView("landing");
          setUserInfo(null);
        }}
        onBackToSearch={() => setCurrentView("search")}
        onProfileUpdate={handleProfileUpdate}
      />
    );
  }

  /**
   * Fallback View
   * 
   * Default view if no valid route matches.
   * Provides navigation back to landing page.
   */
  return (
    <div className="auth-page">
      <div className="w-full max-w-lg panel fade-up text-center">
        <h1 className="header-xl mb-6">Welcome to Flavor Quest</h1>
        <p className="subtle mb-6">Let's get you started</p>
        <button 
          onClick={() => setCurrentView("landing")}
          className="btn btn-primary"
        >
          Go to Landing Page
        </button>
      </div>
    </div>
  );
}

export default App;