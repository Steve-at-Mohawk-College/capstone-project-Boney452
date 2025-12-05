/**
 * PostCSS Configuration
 * 
 * PostCSS configuration for processing CSS with Tailwind CSS and Autoprefixer.
 * 
 * @module postcss.config
 * 
 * @description
 * Plugins:
 * - @tailwindcss/postcss: Tailwind CSS v4 PostCSS plugin
 * - autoprefixer: Automatically adds vendor prefixes for browser compatibility
 * 
 * @note
 * This configuration uses Tailwind CSS v4's new PostCSS plugin format.
 * The plugin processes @tailwind directives and utility classes.
 */

import tailwindcss from '@tailwindcss/postcss';
import autoprefixer from 'autoprefixer';

export default {
  plugins: [
    tailwindcss(), // Tailwind CSS v4 PostCSS plugin
    autoprefixer(), // Automatically add vendor prefixes
  ],
}

