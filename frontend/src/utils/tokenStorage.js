/**
 * Token Storage Utility Module
 * 
 * Provides secure storage and retrieval of authentication tokens using browser
 * sessionStorage. Tokens are automatically cleared when the browser session ends.
 * 
 * @module tokenStorage
 * 
 * @description
 * This module implements a safe wrapper around sessionStorage to handle:
 * - Server-side rendering compatibility (checks for window object)
 * - Error handling for storage quota exceeded or disabled storage
 * - Consistent token key management
 * 
 * @security
 * - Uses sessionStorage (tokens cleared on browser close)
 * - No sensitive data stored in localStorage (persistent)
 * - Handles storage errors gracefully
 */

const TOKEN_KEY = "token";

/**
 * Safely accesses sessionStorage with error handling
 * 
 * @returns {Storage|null} sessionStorage object or null if unavailable
 * @private
 */
const safeSessionStorage = () => {
  // Check for SSR environment (Next.js, etc.)
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    // Storage may be disabled or quota exceeded
    return null;
  }
};

/**
 * Token Storage API
 * 
 * Provides methods to get, set, and remove authentication tokens.
 * All operations are safe and handle errors gracefully.
 * 
 * @namespace tokenStorage
 */
export const tokenStorage = {
  /**
   * Retrieves the authentication token from sessionStorage
   * 
   * @returns {string} Authentication token or empty string if not found
   * 
   * @example
   * const token = tokenStorage.get();
   * if (token) {
   *   // Use token for authenticated requests
   * }
   */
  get() {
    const storage = safeSessionStorage();
    if (!storage) return "";
    return storage.getItem(TOKEN_KEY) || "";
  },
  
  /**
   * Stores an authentication token in sessionStorage
   * 
   * @param {string} token - JWT authentication token to store
   * 
   * @example
   * tokenStorage.set("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...");
   */
  set(token) {
    const storage = safeSessionStorage();
    if (!storage) return;
    if (token) {
      storage.setItem(TOKEN_KEY, token);
    } else {
      // If token is empty/null, remove it
      storage.removeItem(TOKEN_KEY);
    }
  },
  
  /**
   * Removes the authentication token from sessionStorage
   * 
   * Used during logout or when token is invalidated.
   * 
   * @example
   * tokenStorage.remove();
   */
  remove() {
    const storage = safeSessionStorage();
    if (!storage) return;
    storage.removeItem(TOKEN_KEY);
  }
};

