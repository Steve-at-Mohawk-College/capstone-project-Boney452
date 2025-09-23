import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the main heading', () => {
    render(<App />)
    expect(screen.getByText('Flavor Quest 🍽️')).toBeInTheDocument()
  })

  it('renders the instruction text', () => {
    render(<App />)
    expect(screen.getByText('Open your browser console to see the API response.')).toBeInTheDocument()
  })
})
