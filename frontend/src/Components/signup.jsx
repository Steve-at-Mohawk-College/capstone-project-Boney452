import { useState } from "react";
import axios from "axios";

const API_BASE = "http://localhost:5002";

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

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      setIsLoading(false);
      return;
    }
    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      setIsLoading(false);
      return;
    }

    try {
      const { confirmPassword, ...payload } = formData;
      const res = await axios.post(`${API_BASE}/signup`, payload);
      setSuccess(res.data.message || "Account created successfully!");
      setFormData({ username: "", email: "", password: "", confirmPassword: "" });
      setTimeout(() => onSwitchToLogin(), 1200);
    } catch (err) {
      setError(err.response?.data?.error || "Signup failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

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