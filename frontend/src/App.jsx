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
      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-green-50 via-blue-50 to-purple-50">
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
      <div className="w-full h-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="w-full max-w-lg">
          {/* App Name */}
          <div className="text-center mb-16" style={{marginBottom: '4rem'}}>
            <h1 className="text-5xl font-bold text-slate-900 mb-4 tracking-tight" style={{fontSize: '3rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '1rem'}}>Flavor Quest</h1>
            <p className="text-slate-600 text-xl font-medium" style={{color: '#475569', fontSize: '1.25rem', fontWeight: '500'}}>Discover Amazing Flavors</p>
            <p className="text-slate-500 text-base mt-2" style={{color: '#64748b', fontSize: '1rem', marginTop: '0.5rem'}}>Your culinary journey starts here</p>
          </div>

          {/* Action Buttons */}
          <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30" style={{backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: '1.5rem', padding: '3rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
            <div className="space-y-8" style={{display: 'flex', flexDirection: 'column', gap: '2rem'}}>
              {/* Create New Account Button */}
              <button
                onClick={() => setCurrentView("signup")}
                className="w-full py-5 px-8 bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 text-white rounded-xl hover:from-blue-700 hover:via-blue-800 hover:to-indigo-800 focus:ring-4 focus:ring-blue-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98]"
                style={{width: '100%', padding: '1.25rem 2rem', backgroundColor: '#2563eb', color: 'white', borderRadius: '0.75rem', fontSize: '1.125rem', fontWeight: '600', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}
              >
                Create New Account
              </button>

              {/* Sign In Button */}
              <button
                onClick={() => setCurrentView("login")}
                className="w-full py-5 px-8 bg-gradient-to-r from-emerald-500 via-emerald-600 to-teal-600 text-white rounded-xl hover:from-emerald-600 hover:via-emerald-700 hover:to-teal-700 focus:ring-4 focus:ring-emerald-500/30 focus:ring-offset-2 transition-all duration-300 font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98]"
                style={{width: '100%', padding: '1.25rem 2rem', backgroundColor: '#10b981', color: 'white', borderRadius: '0.75rem', fontSize: '1.125rem', fontWeight: '600', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}
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
