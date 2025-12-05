/**
 * Tailwind CSS Configuration
 * 
 * Configuration for Tailwind CSS utility-first CSS framework.
 * Defines content paths for purging unused styles and theme customization.
 * 
 * @module tailwind.config
 * @type {import('tailwindcss').Config}
 * 
 * @description
 * Configuration includes:
 * - Content paths: Files to scan for Tailwind class usage
 * - Theme: Custom theme extensions (currently using defaults)
 * - Plugins: Additional Tailwind plugins (none currently)
 * 
 * @note
 * Tailwind CSS v4 uses a different configuration approach.
 * This config file is for compatibility and basic settings.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html", // Main HTML file
    "./src/**/*.{js,ts,jsx,tsx}", // All JavaScript/TypeScript files in src
  ],
  theme: {
    extend: {}, // Custom theme extensions (empty = use defaults)
  },
  plugins: [], // Additional Tailwind plugins
}

