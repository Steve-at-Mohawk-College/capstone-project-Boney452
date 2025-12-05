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
  const [currentView, setCurrentView] = useState("landing"); // "landing", "login", "signup", "search", "results", "chat"
  const [token, setToken] = useState(tokenStorage.get());
  const [userInfo, setUserInfo] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(!!tokenStorage.get()); // Show loading if we have a token to check


  // Fetch user info on component mount if token exists and redirect to search
  useEffect(() => {
    if (token && !userInfo) {
      const fetchUserInfo = async () => {
        try {
          // Add timeout to prevent infinite loading
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
          
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
          // Clear token and show landing page
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
      setIsLoading(false);
    }
  }, [token, userInfo]);

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
    }
    
    // Navigate to search page after login
    setCurrentView("search");
  };

  const handleSignupSuccess = () => {
    setCurrentView("login");
  };

  const handleSearchResults = (results, query) => {
    setSearchResults(results);
    setSearchQuery(query);
    setCurrentView("results");
  };

  const handleBackToSearch = () => {
    setCurrentView("search");
  };

  const handleProfileUpdate = (updatedUserInfo) => {
    setUserInfo(updatedUserInfo);
  };

  // Check if current user is an admin
  const isAdmin = () => {
    if (!userInfo) return false;
    // Check is_admin from database
    return userInfo.IsAdmin === true;
  };

  // Loading screen while checking authentication
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

  // Landing Page
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
          <div className="flex flex-col items-center space-y-4 w-full">
            {/* Create New Account Button */}
            <button
              onClick={() => setCurrentView("signup")}
              className="btn btn-primary text-xl w-full sm:w-auto"
              style={{ 
                minWidth: '320px',
                padding: '1rem 4rem',
                fontSize: '1.25rem'
              }}
            >
              Create New Account
            </button>

            {/* Sign In Button */}
            <button
              onClick={() => setCurrentView("login")}
              className="btn btn-secondary text-xl w-full sm:w-auto"
              style={{ 
                minWidth: '320px',
                padding: '1rem 4rem',
                fontSize: '1.25rem'
              }}
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Login or Signup pages
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

  // Search Page (after login)
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

  // Results Page
  if (currentView === "results") {
    return (
      <div className="dashboard-page w-full">
        {/* Top bar */}
        <div className="w-full max-w-6xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sm:gap-0 mb-6">
          <div className="flex items-center gap-4">
            <button 
              onClick={handleBackToSearch}
              className="btn btn-ghost"
            >
              ← Back to Search
            </button>
            <h1 className="header-xl fade-up">Search Results</h1>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 w-full sm:w-auto">
            <button 
              onClick={() => setCurrentView("chat")} 
              className="btn btn-ghost whitespace-nowrap"
            >
              💬 Chat
            </button>
            {isAdmin() && (
              <button 
                onClick={() => setCurrentView("users")} 
                className="btn btn-ghost whitespace-nowrap"
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
              className="btn btn-secondary whitespace-nowrap"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Search query display */}
        <div className="w-full max-w-6xl mx-auto px-4 sm:px-6">
          <div className="panel fade-up">
            <div className="text-center">
              <h2 className="text-lg sm:text-xl font-bold text-slate-900 mb-2">
                Restaurants in <span className="text-blue-700">{searchQuery}</span>
              </h2>
              <p className="text-sm sm:text-base text-slate-600">Discover amazing dining experiences</p>
            </div>
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
    );
  }

  // User Management Page (Admin only)
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

  // Chat Page
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

  // Profile Page
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

  // Fallback - redirect to landing
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