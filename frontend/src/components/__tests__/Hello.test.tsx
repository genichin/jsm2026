import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Hello } from '../Hello'

describe('Hello component', () => {
  it('renders greeting with provided name', () => {
    render(<Hello name="J" />)
    expect(screen.getByText(/Hello, J/)).toBeInTheDocument()
  })

  it('renders greeting with default name when no name provided', () => {
    render(<Hello />)
    expect(screen.getByText(/Hello, World/)).toBeInTheDocument()
  })
})
