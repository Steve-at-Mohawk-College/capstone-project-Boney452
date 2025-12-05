/**
 * Main Entry Point for Flavor Quest Application
 * 
 * This file initializes the React application and renders the root App component.
 * It uses React 18's createRoot API for optimal performance and StrictMode for
 * development-time checks and warnings.
 * 
 * @module main
 * @requires react
 * @requires react-dom/client
 * @requires ./index.css - Global styles and TailwindCSS configuration
 * @requires ./App.jsx - Main application component
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

/**
 * Initialize and render the React application
 * 
 * Creates a root container and renders the App component with StrictMode enabled.
 * StrictMode helps identify potential problems in development by:
 * - Identifying components with unsafe lifecycles
 * - Warning about legacy string ref API usage
 * - Detecting unexpected side effects
 */
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
