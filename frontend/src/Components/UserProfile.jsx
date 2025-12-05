/**
 * User Profile Component
 * 
 * User account management interface allowing users to:
 * - Update username
 * - Change password
 * - Delete account
 * 
 * @component
 * @module UserProfile
 * 
 * @param {Object} userInfo - Current authenticated user information
 * @param {Function} onSignOut - Callback for user sign out
 * @param {Function} onBackToSearch - Callback to navigate back to search page
 * @param {Function} onProfileUpdate - Callback when profile is updated, receives updated user info
 * 
 * @description
 * Features:
 * - Tab-based interface (Username, Password, Delete Account)
 * - Form validation (username format, password strength)
 * - Password confirmation for security
 * - Account deletion with password confirmation
 * - CSRF token protection
 * - Loading states and error handling
 * 
 * @security
 * - All inputs sanitized before submission
 * - Password required for account deletion
 * - CSRF tokens for state-changing operations
 * - Current password required for password changes
 */

import { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "../config";
import { tokenStorage } from "../utils/tokenStorage";
import { csrfManager, sanitizeInput, validateUsername, validatePassword } from "../utils/security";

function UserProfile({ userInfo, onSignOut, onBackToSearch, onProfileUpdate }) {
  const [formData, setFormData] = useState({
    username: "",
    currentPassword: "",
    newPassword: "",
    confirmPassword: ""
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [activeTab, setActiveTab] = useState("username"); // "username", "password", or "delete"
  const [deletePassword, setDeletePassword] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (userInfo) {
      setFormData(prev => ({
        ...prev,
        username: userInfo.UserName || ""
      }));
    }
  }, [userInfo]);

  // Clear messages after 3 seconds
  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => {
        setError("");
        setSuccess("");
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [error, success]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError("");
  };

  const handleUpdateUsername = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccess("");

    // Validate username
    if (!formData.username.trim()) {
      setError("Username cannot be empty.");
      setIsLoading(false);
      return;
    }

    if (!validateUsername(formData.username)) {
      setError("Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens");
      setIsLoading(false);
      return;
    }

    // Check if username changed
    if (formData.username === userInfo.UserName) {
      setError("Please enter a different username.");
      setIsLoading(false);
      return;
    }

    try {
      const token = tokenStorage.get();
      if (!token) {
        setError("Authentication required. Please sign in to continue.");
        setIsLoading(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      
      const response = await axios.put(
        `${API_BASE_URL}/me`,
        {
          username: sanitizeInput(formData.username, 50)
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken
          }
        }
      );

      setSuccess("Username updated successfully!");
      
      // Update user info in parent component
      if (onProfileUpdate && response.data.user) {
        onProfileUpdate(response.data.user);
      }

      // Clear form
      setFormData(prev => ({
        ...prev,
        username: response.data.user.UserName
      }));
    } catch (err) {
      setError(err.response?.data?.error || "Unable to update username. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccess("");

    // Validate passwords
    if (!formData.currentPassword) {
      setError("Current password is required.");
      setIsLoading(false);
      return;
    }

    if (!formData.newPassword) {
      setError("New password is required.");
      setIsLoading(false);
      return;
    }

    if (!validatePassword(formData.newPassword)) {
      setError("Password must be at least 8 characters long with uppercase, lowercase, and number");
      setIsLoading(false);
      return;
    }

    if (formData.newPassword !== formData.confirmPassword) {
      setError("New passwords do not match.");
      setIsLoading(false);
      return;
    }

    if (formData.currentPassword === formData.newPassword) {
      setError("New password must be different from your current password.");
      setIsLoading(false);
      return;
    }

    try {
      const token = tokenStorage.get();
      if (!token) {
        setError("Authentication required. Please sign in to continue.");
        setIsLoading(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      
      const response = await axios.put(
        `${API_BASE_URL}/me`,
        {
          password: formData.newPassword,
          current_password: formData.currentPassword
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken
          }
        }
      );

      setSuccess("Password updated successfully!");
      
      // Update user info in parent component if provided
      if (onProfileUpdate && response.data.user) {
        onProfileUpdate(response.data.user);
      }

      // Clear password fields
      setFormData(prev => ({
        ...prev,
        currentPassword: "",
        newPassword: "",
        confirmPassword: ""
      }));
    } catch (err) {
      setError(err.response?.data?.error || "Unable to update password. Please verify your current password and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccess("");

    if (!deletePassword) {
      setError("Password confirmation is required to delete your account.");
      setIsLoading(false);
      return;
    }

    // Final confirmation
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true);
      setIsLoading(false);
      return;
    }

    // Double confirmation
    const finalConfirm = window.confirm(
      "⚠️ WARNING: This action cannot be undone!\n\n" +
      "Deleting your account will permanently remove:\n" +
      "• Your profile and account information\n" +
      "• All your restaurant ratings and reviews\n" +
      "• Your group memberships and messages\n\n" +
      "Are you absolutely sure you want to delete your account?"
    );

    if (!finalConfirm) {
      setShowDeleteConfirm(false);
      setDeletePassword("");
      setIsLoading(false);
      return;
    }

    try {
      const token = tokenStorage.get();
      if (!token) {
        setError("Authentication required. Please sign in to continue.");
        setIsLoading(false);
        return;
      }

      const csrfToken = await csrfManager.getToken();
      
      // Use axios config format for DELETE with body
      await axios({
        method: 'delete',
        url: `${API_BASE_URL}/me`,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken
        },
        data: {
          password: deletePassword
        }
      });

      // Account deleted successfully - sign out and redirect
      setSuccess("Your account has been deleted successfully.");
      
      // Clear token and redirect after a short delay
      setTimeout(() => {
        tokenStorage.remove();
        if (onSignOut) {
          onSignOut();
        }
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.error || "Unable to delete account. Please verify your password and try again.");
      setShowDeleteConfirm(false);
      setDeletePassword("");
    } finally {
      setIsLoading(false);
    }
  };

  if (!userInfo) {
    return (
      <div className="auth-page">
        <div className="w-full max-w-lg panel fade-up text-center">
          <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
          <p className="text-gray-600 mb-4">Please sign in to access your profile.</p>
          <button 
            onClick={onSignOut}
            className="btn btn-primary"
          >
            Go to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header Bar - Back button far left, Sign Out far right */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4">
          <div className="flex items-center justify-between gap-2">
            {typeof onBackToSearch === 'function' && (
              <button
                onClick={onBackToSearch}
                className="btn btn-secondary text-xs sm:text-sm px-3 sm:px-4 py-2"
              >
                ← Back
              </button>
            )}
            <div className="flex-1"></div>
            <button 
              onClick={onSignOut}
              className="btn btn-secondary text-xs sm:text-sm px-3 sm:px-4 py-2"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Page Title */}
        <h1 className="header-xl text-2xl sm:text-3xl md:text-4xl mb-4 sm:mb-6">My Profile</h1>

        {/* User Info Card */}
        <div className="glass p-4 sm:p-6 rounded-lg border border-slate-200/70 mb-4 sm:mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-4 mb-3 sm:mb-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl sm:text-2xl font-bold">
              {userInfo.UserName ? userInfo.UserName.charAt(0).toUpperCase() : "U"}
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-slate-900">{userInfo.UserName}</h2>
              <p className="text-sm sm:text-base text-slate-600 break-words">{userInfo.UserEmail}</p>
              {userInfo.IsAdmin && (
                <span className="inline-block mt-2 px-2 sm:px-3 py-1 bg-blue-100 text-blue-800 text-xs sm:text-sm font-semibold rounded-full">
                  Admin
                </span>
              )}
            </div>
          </div>
          {userInfo.CreatedAt && (
            <p className="text-sm text-slate-500">
              Member since {new Date(userInfo.CreatedAt).toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </p>
          )}
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div 
            className="glass p-3 rounded-lg border border-red-200/70 text-red-700 text-sm mb-4"
            role="alert"
            aria-live="polite"
            aria-atomic="true"
          >
            {error}
          </div>
        )}
        {success && (
          <div 
            className="glass p-3 rounded-lg border border-green-200/70 text-green-800 text-sm mb-4"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            {success}
          </div>
        )}

        {/* Tabs */}
        <div className="flex flex-col sm:flex-row gap-2 mb-4 sm:mb-6 border-b border-slate-200 overflow-x-auto">
          <button
            onClick={() => {
              setActiveTab("username");
              setError("");
              setSuccess("");
              setShowDeleteConfirm(false);
            }}
            className={`px-4 sm:px-6 py-2 sm:py-3 text-sm sm:text-base font-semibold transition-colors whitespace-nowrap ${
              activeTab === "username"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Change Username
          </button>
          <button
            onClick={() => {
              setActiveTab("password");
              setError("");
              setSuccess("");
              setShowDeleteConfirm(false);
            }}
            className={`px-4 sm:px-6 py-2 sm:py-3 text-sm sm:text-base font-semibold transition-colors whitespace-nowrap ${
              activeTab === "password"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Change Password
          </button>
          <button
            onClick={() => {
              setActiveTab("delete");
              setError("");
              setSuccess("");
              setShowDeleteConfirm(false);
              setDeletePassword("");
            }}
            className={`px-4 sm:px-6 py-2 sm:py-3 text-sm sm:text-base font-semibold transition-colors whitespace-nowrap ${
              activeTab === "delete"
                ? "text-red-600 border-b-2 border-red-600"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Delete Account
          </button>
        </div>

        {/* Username Update Form */}
        {activeTab === "username" && (
          <div className="glass p-4 sm:p-6 rounded-lg border border-slate-200/70">
            <h3 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Update Username</h3>
            <form onSubmit={handleUpdateUsername} className="space-y-5">
              <div>
                <label htmlFor="username" className="block text-sm font-bold text-slate-700 mb-2">
                  New Username
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  value={formData.username}
                  onChange={handleChange}
                  className="input w-full"
                  placeholder="Enter new username"
                  required
                  disabled={isLoading}
                  aria-describedby={error ? "username-error" : "username-hint"}
                  aria-invalid={error ? "true" : "false"}
                />
                <span id="username-hint" className="sr-only">
                  Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens
                </span>
              </div>
              <button 
                type="submit" 
                disabled={isLoading || !formData.username.trim() || formData.username === userInfo.UserName}
                className="btn btn-primary w-full"
                aria-busy={isLoading}
                aria-live="polite"
              >
                {isLoading ? "Updating..." : "Update Username"}
              </button>
            </form>
          </div>
        )}

        {/* Password Change Form */}
        {activeTab === "password" && (
          <div className="glass p-4 sm:p-6 rounded-lg border border-slate-200/70">
            <h3 className="text-lg sm:text-xl font-semibold mb-3 sm:mb-4">Change Password</h3>
            <form onSubmit={handleChangePassword} className="space-y-5">
              <div>
                <label htmlFor="currentPassword" className="block text-sm font-bold text-slate-700 mb-2">
                  Current Password
                </label>
                <input
                  id="currentPassword"
                  name="currentPassword"
                  type="password"
                  value={formData.currentPassword}
                  onChange={handleChange}
                  className="input w-full"
                  placeholder="Enter your current password"
                  required
                  disabled={isLoading}
                  aria-describedby="current-password-hint"
                />
                <span id="current-password-hint" className="sr-only">
                  Enter your current password to verify your identity
                </span>
              </div>

              <div>
                <label htmlFor="newPassword" className="block text-sm font-bold text-slate-700 mb-2">
                  New Password
                </label>
                <input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  value={formData.newPassword}
                  onChange={handleChange}
                  className="input w-full"
                  placeholder="Enter new password"
                  required
                  disabled={isLoading}
                  aria-describedby="new-password-hint"
                />
                <span id="new-password-hint" className="sr-only">
                  Password must be at least 8 characters with uppercase, lowercase, and number
                </span>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-bold text-slate-700 mb-2">
                  Confirm New Password
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="input w-full"
                  placeholder="Confirm new password"
                  required
                  disabled={isLoading}
                  aria-describedby="confirm-password-hint"
                />
                <span id="confirm-password-hint" className="sr-only">
                  Re-enter your new password to confirm
                </span>
              </div>

              <button 
                type="submit" 
                disabled={isLoading || !formData.currentPassword || !formData.newPassword || !formData.confirmPassword}
                className="btn btn-primary w-full"
                aria-busy={isLoading}
                aria-live="polite"
              >
                {isLoading ? "Updating..." : "Change Password"}
              </button>
            </form>
          </div>
        )}

        {/* Delete Account Form */}
        {activeTab === "delete" && (
          <div className="glass p-4 sm:p-6 rounded-lg border border-red-200/70 bg-red-50/30">
            <div className="mb-3 sm:mb-4">
              <h3 className="text-lg sm:text-xl font-semibold text-red-900 mb-2">Delete Account</h3>
              <p className="text-xs sm:text-sm text-red-700 mb-3 sm:mb-4">
                This action cannot be undone. Deleting your account will permanently remove all your data including:
              </p>
              <ul className="list-disc list-inside text-xs sm:text-sm text-red-700 mb-3 sm:mb-4 space-y-1">
                <li>Your profile and account information</li>
                <li>All your restaurant ratings and reviews</li>
                <li>Your group memberships and messages</li>
              </ul>
            </div>

            {!showDeleteConfirm ? (
              <div className="space-y-4">
                <p className="text-sm font-semibold text-red-800">
                  To confirm account deletion, please enter your password:
                </p>
                <form onSubmit={handleDeleteAccount} className="space-y-4">
                  <div>
                    <label htmlFor="deletePassword" className="block text-sm font-bold text-slate-700 mb-2">
                      Confirm Password
                    </label>
                    <input
                      id="deletePassword"
                      name="deletePassword"
                      type="password"
                      value={deletePassword}
                      onChange={(e) => setDeletePassword(e.target.value)}
                      className="input w-full"
                      placeholder="Enter your password to confirm"
                      required
                      disabled={isLoading}
                      aria-describedby="delete-password-hint"
                    />
                    <span id="delete-password-hint" className="sr-only">
                      Enter your password to confirm account deletion
                    </span>
                  </div>
                  <button 
                    type="submit" 
                    disabled={isLoading || !deletePassword}
                    className="btn w-full text-white font-semibold"
                    style={{
                      background: isLoading || !deletePassword 
                        ? 'linear-gradient(135deg, #dc2626, #b91c1c)' 
                        : 'linear-gradient(135deg, #ef4444, #dc2626)',
                      border: 'none',
                      boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                    }}
                    onMouseEnter={(e) => {
                      if (!isLoading && deletePassword) {
                        e.target.style.background = 'linear-gradient(135deg, #dc2626, #b91c1c)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isLoading && deletePassword) {
                        e.target.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                      }
                    }}
                    aria-busy={isLoading}
                    aria-live="polite"
                  >
                    {isLoading ? "Processing..." : "Continue to Delete Account"}
                  </button>
                </form>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-4 bg-red-100 border-2 border-red-400 rounded-lg">
                  <p className="font-bold text-red-900 mb-2">⚠️ Final Confirmation Required</p>
                  <p className="text-sm text-red-800 mb-4">
                    You are about to permanently delete your account. This action cannot be undone.
                  </p>
                  <p className="text-sm font-semibold text-red-900">
                    Password: {deletePassword ? "✓ Entered" : "Not entered"}
                  </p>
                </div>
                <form onSubmit={handleDeleteAccount} className="space-y-4">
                  <button 
                    type="submit" 
                    disabled={isLoading}
                    className="btn w-full bg-red-600 hover:bg-red-700 text-white font-bold"
                    aria-busy={isLoading}
                    aria-live="polite"
                  >
                    {isLoading ? "Deleting Account..." : "⚠️ Yes, Delete My Account Permanently"}
                  </button>
                  <button 
                    type="button"
                    onClick={() => {
                      setShowDeleteConfirm(false);
                      setDeletePassword("");
                      setError("");
                    }}
                    disabled={isLoading}
                    className="btn btn-secondary w-full"
                  >
                    Cancel
                  </button>
                </form>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default UserProfile;

