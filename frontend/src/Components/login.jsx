import { useState } from "react";
import axios from "axios";
import { sanitizeInput, validateEmail } from "../utils/security";
import { API_BASE_URL } from "../config";
import { tokenStorage } from "../utils/tokenStorage";

const Login = ({ onLoginSuccess, onSwitchToSignup, onBackToLanding }) => {
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    // Validate email format
    if (!validateEmail(formData.email)) {
      setError("Please enter a valid email address");
      setIsLoading(false);
      return;
    }

    try {
      // Convert email to lowercase for case-insensitive login
      const loginData = {
        ...formData,
        email: formData.email.toLowerCase().trim()
      };
      const res = await axios.post(`${API_BASE_URL}/login`, loginData);
      const token = res.data.token;
      tokenStorage.set(token);
      onLoginSuccess(token);
      setFormData({ email: "", password: "" });
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    const sanitizedValue = sanitizeInput(value, 100);
    setFormData({ ...formData, [name]: sanitizedValue });
  };

  return (
    <div className="auth-page">
      <div className="w-full max-w-xl panel fade-up">
        <div className="text-center mb-8">
          <h1 className="header-xl">Welcome back</h1>
          <p className="subtle">Sign in to continue your Flavor Quest</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="email" className="block text-sm font-bold text-slate-700 mb-2">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="input"
              placeholder="you@example.com"
              aria-describedby={error ? "login-error" : undefined}
              aria-invalid={error ? "true" : "false"}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-bold text-slate-700 mb-2">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              required
              value={formData.password}
              onChange={handleChange}
              className="input"
              placeholder="••••••••"
              aria-describedby={error ? "login-error" : undefined}
              aria-invalid={error ? "true" : "false"}
            />
          </div>

          {error && (
            <div 
              id="login-error"
              className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm"
              role="alert"
              aria-live="polite"
              aria-atomic="true"
            >
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={isLoading} 
            className="btn btn-primary w-full"
            aria-busy={isLoading}
            aria-live="polite"
          >
            {isLoading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm text-slate-600">
            Don't have an account?{" "}
            <button onClick={onSwitchToSignup} className="font-semibold text-blue-600 hover:underline">
              Create one
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;