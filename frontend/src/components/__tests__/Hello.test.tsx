import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Hello } from '../Hello';

describe('Hello', () => {
  it('renders with provided name', () => {
    render(<Hello name="J" />);
    expect(screen.getByText('Hello, J')).toBeInTheDocument();
  });

  it('renders with default name when no name is provided', () => {
    render(<Hello />);
    expect(screen.getByText('Hello, World')).toBeInTheDocument();
  });
});
