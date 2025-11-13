import { useState } from "react";
import axios from "axios";
import { sanitizeInput, validateEmail, validateUsername, validatePassword, csrfManager } from "../utils/security";
import { API_BASE_URL } from "../config";

const Signup = ({ onSignupSuccess, onSwitchToLogin, onBackToLanding }) => {
  const [formData, setFormData] = useState({ username: "", email: "", password: "", confirmPassword: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccess("");

    // Validate inputs
    if (!validateUsername(formData.username)) {
      setError("Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens");
      setIsLoading(false);
      return;
    }

    if (!validateEmail(formData.email)) {
      setError("Please enter a valid email address");
      setIsLoading(false);
      return;
    }

    if (!validatePassword(formData.password)) {
      setError("Password must be at least 8 characters long with uppercase, lowercase, and number");
      setIsLoading(false);
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      setIsLoading(false);
      return;
    }

    try {
      const { confirmPassword, ...payload } = formData;
      const csrfToken = await csrfManager.getToken();
      const headers = {
        ...csrfManager.getHeaders(),
        'Content-Type': 'application/json'
      };
      const res = await axios.post(`${API_BASE_URL}/signup`, payload, { headers });
      setSuccess(res.data.message || "Account created successfully!");
      setFormData({ username: "", email: "", password: "", confirmPassword: "" });
      setTimeout(() => onSwitchToLogin(), 1200);
    } catch (err) {
      setError(err.response?.data?.error || "Signup failed. Please try again.");
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
          <h1 className="header-xl">Create your account</h1>
          <p className="subtle">Join Flavor Quest and start exploring</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="username" className="block text-sm font-bold text-slate-700 mb-2">Username</label>
            <input
              id="username"
              name="username"
              type="text"
              required
              value={formData.username}
              onChange={handleChange}
              className="input"
              placeholder="Your display name"
            />
          </div>

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
              placeholder="At least 6 characters"
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-bold text-slate-700 mb-2">Confirm Password</label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              value={formData.confirmPassword}
              onChange={handleChange}
              className="input"
              placeholder="Repeat your password"
            />
          </div>

          {error && (
            <div className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm">{error}</div>
          )}
          {success && (
            <div className="glass p-3 rounded-lg border border-green-200/70 text-green-800 text-sm">{success}</div>
          )}

          <button type="submit" disabled={isLoading} className="btn btn-primary w-full">
            {isLoading ? "Creating…" : "Create Account"}
          </button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm text-slate-600">
            Already have an account?{" "}
            <button onClick={onSwitchToLogin} className="font-semibold text-blue-600 hover:underline">
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Signup;