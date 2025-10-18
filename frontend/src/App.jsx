import { useState, useEffect } from "react";
import Login from "./Components/login";
import Signup from "./Components/signup";
import RestaurantSearch from "./Components/RestaurantSearch";
import UserManagement from "./Components/UserManagement";

function App() {
  const [currentView, setCurrentView] = useState("landing"); // "landing", "login", or "signup"
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [dashboardView, setDashboardView] = useState("search"); // "search" or "users"
  const [userInfo, setUserInfo] = useState(null);

  console.log("App component is rendering, currentView:", currentView, "token:", token);

  // Fetch user info on component mount if token exists
  useEffect(() => {
    if (token && !userInfo) {
      const fetchUserInfo = async () => {
        try {
          const response = await fetch("http://localhost:5002/me", {
            headers: {
              "Authorization": `Bearer ${token}`
            }
          });
          if (response.ok) {
            const data = await response.json();
            setUserInfo(data.user);
          }
        } catch (error) {
          console.error("Failed to fetch user info:", error);
        }
      };
      fetchUserInfo();
    }
  }, [token, userInfo]);

  const handleLoginSuccess = async (newToken) => {
    setToken(newToken);
    console.log("Login successful, token:", newToken);
    
    // Fetch user info to check if they're an admin
    try {
      const response = await fetch("http://localhost:5002/me", {
        headers: {
          "Authorization": `Bearer ${newToken}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setUserInfo(data.user);
      }
    } catch (error) {
      console.error("Failed to fetch user info:", error);
    }
  };

  const handleSignupSuccess = () => {
    setCurrentView("login");
  };

  // Check if current user is an admin
  const isAdmin = () => {
    if (!userInfo) return false;
    // Define admin users - you can modify this list
    const adminUsers = ["Boney123", "admin", "administrator"];
    return adminUsers.includes(userInfo.UserName);
  };

  // If user is already logged in, show dashboard with navigation
  if (token) {
    return (
      <div className="w-full min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">

        {/* Enhanced Dashboard Content */}
        {dashboardView === "search" ? (
          <RestaurantSearch onSignOut={() => {
            localStorage.removeItem("token");
            setToken("");
            setCurrentView("landing");
          }} />
        ) : isAdmin() ? (
          <UserManagement onSignOut={() => {
            localStorage.removeItem("token");
            setToken("");
            setCurrentView("landing");
          }} />
        ) : (
          <div className="max-w-6xl mx-auto px-6 py-12">
            <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30 text-center" style={{backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '1.5rem', padding: '3rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
              <h2 className="text-4xl font-bold text-slate-900 mb-6 tracking-tight" style={{fontSize: '2.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '1.5rem'}}>Welcome to Flavor Quest!</h2>
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 border border-blue-200" style={{backgroundColor: 'rgba(239, 246, 255, 0.5)', borderRadius: '1rem', padding: '1.5rem'}}>
                <p className="text-lg text-slate-700 font-medium" style={{fontSize: '1.125rem', color: '#334155', fontWeight: '500'}}>
                  🎉 Your culinary journey starts here! 🍽️
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Enhanced Landing page with signup/login options
  if (currentView === "landing") {
    return (
      <div className="w-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 px-4 auth-page">
        <div className="w-full max-w-lg">
          {/* Enhanced App Name Section */}
          <div className="text-center mb-16" style={{marginBottom: '4rem'}}>
            <h1 className="text-6xl font-bold text-slate-900 mb-6 tracking-tight" style={{fontSize: '3.75rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '1.5rem'}}>Flavor Quest</h1>
            <p className="text-slate-600 text-2xl font-medium mb-3" style={{color: '#475569', fontSize: '1.5rem', fontWeight: '500', marginBottom: '0.75rem'}}>Discover Amazing Flavors</p>
            <p className="text-slate-500 text-lg" style={{color: '#64748b', fontSize: '1.125rem'}}>Your culinary journey starts here</p>
          </div>

          {/* Enhanced Action Buttons */}
          <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30" style={{backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '1.5rem', padding: '3rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
            <div className="space-y-8" style={{display: 'flex', flexDirection: 'column', gap: '2rem'}}>
              {/* Create New Account Button */}
              <button
                onClick={() => setCurrentView("signup")}
                className="w-full py-6 px-8 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white rounded-xl hover:from-blue-700 hover:via-blue-800 hover:to-indigo-800 focus:ring-4 focus:ring-blue-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold text-xl shadow-xl hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98]"
                style={{width: '100%', padding: '1.5rem 2rem', backgroundColor: '#2563eb', color: 'white', borderRadius: '0.75rem', fontSize: '1.25rem', fontWeight: '600', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}
              >
                Create New Account
              </button>

              {/* Sign In Button */}
              <button
                onClick={() => setCurrentView("login")}
                className="w-full py-6 px-8 bg-gradient-to-r from-emerald-500 via-emerald-600 to-teal-600 text-white rounded-xl hover:from-emerald-600 hover:via-emerald-700 hover:to-teal-700 focus:ring-4 focus:ring-emerald-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold text-xl shadow-xl hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98]"
                style={{width: '100%', padding: '1.5rem 2rem', backgroundColor: '#10b981', color: 'white', borderRadius: '0.75rem', fontSize: '1.25rem', fontWeight: '600', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}
              >
                Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Login or Signup pages
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

export default App;