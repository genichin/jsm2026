import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Hello } from '../Hello';

describe('Hello component', () => {
  it('renders the name when provided', () => {
    render(<Hello name="Test User" />);
    expect(screen.getByText('Hello, Test User')).toBeInTheDocument();
  });

  it('renders default "World" when name is not provided', () => {
    render(<Hello />);
    expect(screen.getByText('Hello, World')).toBeInTheDocument();
  });
});
