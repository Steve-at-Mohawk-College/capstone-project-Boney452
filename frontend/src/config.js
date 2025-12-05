/**
 * Application Configuration
 * 
 * Centralized configuration file for API endpoints and environment variables.
 * Uses Vite's environment variable system for configuration management.
 * 
 * @module config
 * 
 * @constant {string} API_BASE_URL - Base URL for backend API requests
 *   - Reads from VITE_API_BASE_URL environment variable
 *   - Falls back to localhost:5002 for development
 *   - Automatically trims whitespace to prevent connection errors
 * 
 * @example
 * // In .env file:
 * VITE_API_BASE_URL=https://flavour-quest-e7ho.onrender.com
 * 
 * // Usage:
 * import { API_BASE_URL } from './config';
 * fetch(`${API_BASE_URL}/me`)
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:5002";

