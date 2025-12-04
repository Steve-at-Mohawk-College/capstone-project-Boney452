const SEARCH_HISTORY_KEY_PREFIX = "flavor_quest_search_history";
const MAX_HISTORY = 3;

const safeLocalStorage = () => {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

/**
 * Get the storage key for a specific user
 * @param {number|string} userId - User ID
 * @returns {string} Storage key
 */
const getStorageKey = (userId) => {
  if (!userId) {
    // Fallback to generic key if no user ID (for backward compatibility)
    return SEARCH_HISTORY_KEY_PREFIX;
  }
  return `${SEARCH_HISTORY_KEY_PREFIX}_user_${userId}`;
};

export const searchHistory = {
  /**
   * Get the last N searches (up to MAX_HISTORY) for a specific user
   * @param {number|string} userId - User ID (optional, for backward compatibility)
   * @returns {string[]} Array of city names
   */
  get(userId = null) {
    const storage = safeLocalStorage();
    if (!storage) return [];
    
    try {
      const key = getStorageKey(userId);
      const history = storage.getItem(key);
      if (!history) return [];
      
      const parsed = JSON.parse(history);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  },

  /**
   * Add a new search to history (keeps only last MAX_HISTORY) for a specific user
   * @param {string} city - City name to add
   * @param {number|string} userId - User ID (optional, for backward compatibility)
   */
  add(city, userId = null) {
    if (!city || !city.trim()) return;
    
    const storage = safeLocalStorage();
    if (!storage) return;
    
    try {
      const key = getStorageKey(userId);
      const currentHistory = this.get(userId);
      const cityTrimmed = city.trim();
      
      // Remove if already exists (to avoid duplicates)
      const filtered = currentHistory.filter(c => c.toLowerCase() !== cityTrimmed.toLowerCase());
      
      // Add to front
      const newHistory = [cityTrimmed, ...filtered].slice(0, MAX_HISTORY);
      
      storage.setItem(key, JSON.stringify(newHistory));
    } catch (error) {
      console.error("Failed to save search history:", error);
    }
  },

  /**
   * Clear all search history for a specific user
   * @param {number|string} userId - User ID (optional, for backward compatibility)
   */
  clear(userId = null) {
    const storage = safeLocalStorage();
    if (!storage) return;
    
    try {
      const key = getStorageKey(userId);
      storage.removeItem(key);
    } catch (error) {
      console.error("Failed to clear search history:", error);
    }
  }
};



