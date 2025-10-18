import { useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:5002";

const Login = ({ onLoginSuccess, onSwitchToSignup, onBackToLanding }) => {
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const res = await axios.post(`${API_BASE}/login`, formData);
      const token = res.data.token;
      localStorage.setItem("token", token);
      onLoginSuccess(token);
      setFormData({ email: "", password: "" });
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="w-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 px-4 auth-page">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-16" style={{marginBottom: '4rem'}}>
          <h1 className="text-5xl font-bold text-slate-900 mb-6 tracking-tight" style={{fontSize: '3rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '1.5rem'}}>Login to your Account</h1>
          <p className="text-slate-600 text-xl font-medium mb-2" style={{color: '#475569', fontSize: '1.25rem', fontWeight: '500', marginBottom: '0.5rem'}}>Welcome back to Flavor Quest</p>
          <p className="text-slate-500 text-base" style={{color: '#64748b', fontSize: '1rem'}}>Continue your culinary adventure</p>
        </div>

        {/* Login Form */}
        <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 border border-white/30" style={{backgroundColor: 'rgba(255, 255, 255, 0.95)', borderRadius: '1.5rem', padding: '3rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'}}>
          <form onSubmit={handleSubmit} className="space-y-8" style={{display: 'flex', flexDirection: 'column', gap: '2rem'}}>
            {/* Email Field */}
            <div className="space-y-4" style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
              <label htmlFor="email" className="block text-sm font-bold text-slate-700" style={{fontSize: '0.875rem', fontWeight: 'bold', color: '#334155'}}>
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="w-full px-5 py-4 border-2 border-slate-200 rounded-xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-300 bg-slate-50/50 focus:bg-white shadow-sm hover:shadow-md"
                style={{width: '100%', padding: '1rem 1.25rem', border: '2px solid #e2e8f0', borderRadius: '0.75rem', backgroundColor: 'rgba(248, 250, 252, 0.5)'}}
                placeholder="Enter your email"
              />
            </div>

            {/* Password Field */}
            <div className="space-y-4" style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
              <label htmlFor="password" className="block text-sm font-bold text-slate-700" style={{fontSize: '0.875rem', fontWeight: 'bold', color: '#334155'}}>
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="w-full px-5 py-4 border-2 border-slate-200 rounded-xl focus:ring-4 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-300 bg-slate-50/50 focus:bg-white shadow-sm hover:shadow-md"
                style={{width: '100%', padding: '1rem 1.25rem', border: '2px solid #e2e8f0', borderRadius: '0.75rem', backgroundColor: 'rgba(248, 250, 252, 0.5)'}}
                placeholder="Enter your password"
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50/80 border-2 border-red-200 rounded-xl p-4 shadow-sm">
                <p className="text-sm font-semibold text-red-800">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-8" style={{paddingTop: '2rem'}}>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-5 px-8 bg-gradient-to-r from-emerald-500 via-emerald-600 to-teal-600 text-white rounded-xl hover:from-emerald-600 hover:via-emerald-700 hover:to-teal-700 focus:ring-4 focus:ring-emerald-500/30 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:scale-[1.02] active:scale-[0.98]"
                style={{width: '100%', padding: '1.25rem 2rem', backgroundColor: '#10b981', color: 'white', borderRadius: '0.75rem', fontSize: '1.125rem', fontWeight: '600', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'}}
              >
                {isLoading ? "Signing in..." : "Sign In"}
              </button>
            </div>
          </form>

          {/* Navigation */}
          <div className="mt-12 text-center" style={{marginTop: '3rem'}}>
            <p className="text-base text-slate-600" style={{fontSize: '1rem', color: '#475569'}}>
              Don't have an account?{" "}
              <button
                onClick={onSwitchToSignup}
                className="text-emerald-600 hover:text-emerald-500 font-semibold transition-all duration-200 hover:underline"
                style={{color: '#10b981', fontWeight: '600'}}
              >
                Sign up here
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;