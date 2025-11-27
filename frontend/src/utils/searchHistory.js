const SEARCH_HISTORY_KEY = "flavor_quest_search_history";
const MAX_HISTORY = 3;

const safeLocalStorage = () => {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
};

export const searchHistory = {
  /**
   * Get the last N searches (up to MAX_HISTORY)
   * @returns {string[]} Array of city names
   */
  get() {
    const storage = safeLocalStorage();
    if (!storage) return [];
    
    try {
      const history = storage.getItem(SEARCH_HISTORY_KEY);
      if (!history) return [];
      
      const parsed = JSON.parse(history);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  },

  /**
   * Add a new search to history (keeps only last MAX_HISTORY)
   * @param {string} city - City name to add
   */
  add(city) {
    if (!city || !city.trim()) return;
    
    const storage = safeLocalStorage();
    if (!storage) return;
    
    try {
      const currentHistory = this.get();
      const cityTrimmed = city.trim();
      
      // Remove if already exists (to avoid duplicates)
      const filtered = currentHistory.filter(c => c.toLowerCase() !== cityTrimmed.toLowerCase());
      
      // Add to front
      const newHistory = [cityTrimmed, ...filtered].slice(0, MAX_HISTORY);
      
      storage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(newHistory));
    } catch (error) {
      console.error("Failed to save search history:", error);
    }
  },

  /**
   * Clear all search history
   */
  clear() {
    const storage = safeLocalStorage();
    if (!storage) return;
    
    try {
      storage.removeItem(SEARCH_HISTORY_KEY);
    } catch (error) {
      console.error("Failed to clear search history:", error);
    }
  }
};

