/**
 * Error Boundary Component
 * 
 * React error boundary that catches JavaScript errors anywhere in the child
 * component tree, logs those errors, and displays a fallback UI instead of
 * crashing the entire application.
 * 
 * @component
 * @module ErrorBoundary
 * 
 * @description
 * This component implements React's error boundary pattern to:
 * - Catch errors during rendering, in lifecycle methods, and in constructors
 * - Display user-friendly error messages instead of white screen
 * - Provide recovery mechanism (Try Again button)
 * - Log errors for debugging
 * 
 * @usage
 * Wrap components that might throw errors:
 * <ErrorBoundary>
 *   <RestaurantCard restaurant={data} />
 * </ErrorBoundary>
 * 
 * @note
 * Error boundaries do NOT catch errors in:
 * - Event handlers (use try/catch)
 * - Asynchronous code (setTimeout, promises)
 * - Server-side rendering
 * - Errors thrown in the error boundary itself
 */

import React from 'react';

class ErrorBoundary extends React.Component {
  /**
   * Initialize error boundary state
   * 
   * @param {Object} props - Component props
   */
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  /**
   * Update state when an error is caught
   * 
   * Called during the render phase, so side effects are not allowed.
   * 
   * @static
   * @param {Error} error - The error that was thrown
   * @returns {Object} State update object
   */
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  /**
   * Log error information when an error is caught
   * 
   * Called after an error has been thrown by a descendant component.
   * Can be used to log errors to an error reporting service.
   * 
   * @param {Error} error - The error that was thrown
   * @param {Object} errorInfo - Component stack trace information
   */
  componentDidCatch(error, errorInfo) {
    // Log error for debugging
    // In production, send to error reporting service (e.g., Sentry, LogRocket)
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flip-card-container fade-up">
          <div className="glass p-4 rounded-xl border border-red-200/70">
            <h4 className="text-red-700 font-semibold mb-2">Something went wrong</h4>
            <p className="text-red-600 text-sm">Unable to display this restaurant card</p>
            <button 
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-2 px-3 py-1 bg-red-100 text-red-700 rounded text-sm hover:bg-red-200"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
