/**
 * Vite Configuration
 * 
 * Build tool configuration for the Flavor Quest frontend application.
 * Vite provides fast development server and optimized production builds.
 * 
 * @module vite.config
 * 
 * @description
 * Configuration includes:
 * - React plugin for JSX/TSX support
 * - Base path for deployment (Netlify)
 * - Build output directory structure
 * 
 * @see https://vite.dev/config/
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/', // Base path for deployment (Netlify requires '/')
  build: {
    outDir: 'dist', // Output directory for production builds
    assetsDir: 'assets', // Directory for static assets (images, fonts, etc.)
  },
})
