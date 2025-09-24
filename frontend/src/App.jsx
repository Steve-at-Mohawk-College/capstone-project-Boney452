import { useState } from "react";
import Login from "./Components/login";
import Signup from "./Components/signup";

function App() {
  const [currentView, setCurrentView] = useState("landing"); // "landing", "login", or "signup"
  const [token, setToken] = useState(localStorage.getItem("token") || "");

  console.log("App component is rendering, currentView:", currentView, "token:", token);

  const handleLoginSuccess = (newToken) => {
    setToken(newToken);
    console.log("Login successful, token:", newToken);
  };

  const handleSignupSuccess = () => {
    setCurrentView("login");
  };

  // If user is already logged in, show a simple dashboard
  if (token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-blue-50 to-purple-50">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full mx-4 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-green-500 to-blue-600 rounded-full mb-4">
            <span className="text-2xl">🎉</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Welcome to Flavor Quest!</h1>
          <p className="text-gray-600 mb-6">You're successfully logged in and ready to explore amazing flavors.</p>
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <p className="text-sm text-gray-500 mb-2">Your session token:</p>
            <p className="text-xs text-gray-700 break-all font-mono">{token}</p>
          </div>
          <button
            onClick={() => {
              localStorage.removeItem("token");
              setToken("");
              setCurrentView("landing");
            }}
            className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-pink-600 text-white rounded-lg hover:from-red-600 hover:to-pink-700 transition duration-200"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  // Landing page with signup/login options
  if (currentView === "landing") {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-full max-w-md px-6">
          {/* App Name */}
          <div className="text-center mb-10">
            <h1 className="text-3xl font-bold text-gray-900 mb-3">Flavor Quest</h1>
            <p className="text-gray-600">Discover Amazing Flavors</p>
          </div>

          {/* Action Buttons */}
          <div className="space-y-6">
            {/* Sign Up Button */}
            <button
              onClick={() => setCurrentView("signup")}
              className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 font-medium"
            >
              Create New Account
            </button>

            {/* Login Button */}
            <button
              onClick={() => setCurrentView("login")}
              className="w-full py-3 px-4 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 font-medium"
            >
              Sign In
            </button>
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
