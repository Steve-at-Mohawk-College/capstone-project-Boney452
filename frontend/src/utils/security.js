import { API_BASE_URL } from "../config";

// Security utilities for frontend XSS protection

/**
 * Sanitize HTML content to prevent XSS attacks
 * @param {string} html - HTML string to sanitize
 * @returns {string} - Sanitized HTML string
 */
export function sanitizeHTML(html) {
  if (!html || typeof html !== 'string') {
    return '';
  }

  // Create a temporary div element
  const temp = document.createElement('div');
  temp.textContent = html;
  return temp.innerHTML;
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
export function escapeHTML(text) {
  if (!text || typeof text !== 'string') {
    return '';
  }

  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
    '/': '&#x2F;'
  };

  return text.replace(/[&<>"'/]/g, (s) => map[s]);
}

/**
 * Validate and sanitize user input
 * @param {string} input - User input to validate
 * @param {number} maxLength - Maximum allowed length
 * @returns {string} - Sanitized input
 */
export function sanitizeInput(input, maxLength = 1000) {
  if (!input || typeof input !== 'string') {
    return '';
  }

  // Remove HTML tags and limit length
  let sanitized = input
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+\s*=/gi, '') // Remove event handlers
    .substring(0, maxLength)
    .trim();

  return sanitized;
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} - True if valid email
 */
export function validateEmail(email) {
  if (!email || typeof email !== 'string') {
    return false;
  }

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test(email);
}

/**
 * Validate username format
 * @param {string} username - Username to validate
 * @returns {boolean} - True if valid username
 */
export function validateUsername(username) {
  if (!username || typeof username !== 'string') {
    return false;
  }

  // Username should be 3-50 characters, alphanumeric with underscores and hyphens
  const usernameRegex = /^[a-zA-Z0-9_-]{3,50}$/;
  return usernameRegex.test(username);
}

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @returns {boolean} - True if password meets requirements
 */
export function validatePassword(password) {
  if (!password || typeof password !== 'string') {
    return false;
  }

  // At least 8 characters, one uppercase, one lowercase, one digit
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
  return passwordRegex.test(password);
}

/**
 * Validate rating value
 * @param {number} rating - Rating to validate
 * @returns {boolean} - True if valid rating
 */
export function validateRating(rating) {
  const num = Number(rating);
  return !isNaN(num) && num >= 1 && num <= 5 && Number.isInteger(num);
}

/**
 * Check if text contains inappropriate content
 * @param {string} text - Text to check
 * @returns {boolean} - True if contains inappropriate content
 */
export function containsInappropriateContent(text) {
  if (!text || typeof text !== 'string') {
    return false;
  }

  const inappropriateWords = [
    // Spam and fraud related
    'spam', 'scam', 'fake', 'fraud', 'hate', 'violence',
    // Adult/profanity words
    'fuck', 'fucking', 'fucked', 'shit', 'shitting', 'damn', 'damned',
    'ass', 'asshole', 'bitch', 'bastard', 'hell', 'crap', 'piss',
    'dick', 'cock', 'pussy', 'whore', 'slut', 'cunt', 'motherfucker',
    'bullshit', 'goddamn', 'goddamned', 'bloody', 'bugger', 'wanker',
    'prick', 'twat', 'tosser', 'bellend', 'arse', 'arsehole',
    // Additional variations
    'f*ck', 'f**k', 's**t', 'sh*t', 'a**', 'a**hole', 'b****', 'b***h',
    'd***', 'c***', 'p***y', 'w***e', 's***', 'c***', 'm***********r',
  ];

  const textLower = text.toLowerCase();
  
  // Check for inappropriate words
  for (const word of inappropriateWords) {
    if (textLower.includes(word)) {
      return true;
    }
  }

  // Check for excessive capitalization (potential spam)
  if (text.length > 10) {
    const capsCount = (text.match(/[A-Z]/g) || []).length;
    const capsRatio = capsCount / text.length;
    if (capsRatio > 0.7) { // More than 70% caps
      return true;
    }
  }

  // Check for excessive repetition (potential spam)
  if (text.length > 20) {
    const words = text.split(/\s+/);
    if (words.length > 3) {
      const wordCounts = {};
      for (const word of words) {
        const wordLower = word.toLowerCase();
        wordCounts[wordLower] = (wordCounts[wordLower] || 0) + 1;
        if (wordCounts[wordLower] > words.length * 0.5) { // Same word more than 50% of text
          return true;
        }
      }
    }
  }

  return false;
}

/**
 * Sanitize restaurant data from API
 * @param {Object} restaurant - Restaurant object to sanitize
 * @returns {Object} - Sanitized restaurant object
 */
export function sanitizeRestaurantData(restaurant) {
  if (!restaurant || typeof restaurant !== 'object') {
    return {};
  }

  return {
    ...restaurant,
    name: sanitizeInput(restaurant.name, 200),
    location: sanitizeInput(restaurant.location, 500),
    cuisine_type: sanitizeInput(restaurant.cuisine_type, 100),
    formatted_address: sanitizeInput(restaurant.formatted_address, 500),
    user_review: restaurant.user_review ? sanitizeInput(restaurant.user_review, 1000) : null
  };
}

/**
 * Create a safe HTML element with sanitized content
 * @param {string} tagName - HTML tag name
 * @param {string} content - Content to insert
 * @param {Object} attributes - HTML attributes
 * @returns {HTMLElement} - Safe HTML element
 */
export function createSafeElement(tagName, content, attributes = {}) {
  const element = document.createElement(tagName);
  
  // Set sanitized content
  element.textContent = content;
  
  // Set safe attributes
  Object.entries(attributes).forEach(([key, value]) => {
    if (key.startsWith('on')) {
      // Skip event handlers to prevent XSS
      return;
    }
    
    if (key === 'href' || key === 'src') {
      // Validate URLs
      try {
        new URL(value);
        element.setAttribute(key, value);
      } catch {
        // Invalid URL, skip
      }
    } else {
      element.setAttribute(key, sanitizeInput(value));
    }
  });
  
  return element;
}

/**
 * Set innerHTML safely
 * @param {HTMLElement} element - Element to set content for
 * @param {string} content - Content to set
 */
export function setSafeInnerHTML(element, content) {
  if (!element || !content) {
    return;
  }
  
  element.innerHTML = sanitizeHTML(content);
}

/**
 * Get safe text content from user input
 * @param {string} input - User input
 * @returns {string} - Safe text content
 */
export function getSafeTextContent(input) {
  if (!input) {
    return '';
  }
  
  const temp = document.createElement('div');
  temp.textContent = input;
  return temp.textContent || temp.innerText || '';
}

/**
 * CSRF Token Management
 */
class CSRFManager {
  constructor() {
    this.token = null;
    this.tokenExpiry = null;
  }

  async getToken() {
    // Check if we have a valid token
    if (this.token && this.tokenExpiry && Date.now() < this.tokenExpiry) {
      return this.token;
    }

    // Fetch new token
    try {
      const response = await fetch(`${API_BASE_URL}/csrf-token`);
      const data = await response.json();
      this.token = data.csrf_token;
      this.tokenExpiry = Date.now() + (50 * 60 * 1000); // 50 minutes (tokens expire in 1 hour)
      return this.token;
    } catch (error) {
      console.error('Failed to fetch CSRF token:', error);
      return null;
    }
  }

  getHeaders() {
    return {
      'X-CSRF-Token': this.token
    };
  }

  clearToken() {
    this.token = null;
    this.tokenExpiry = null;
  }
}

// Export singleton instance
export const csrfManager = new CSRFManager();
