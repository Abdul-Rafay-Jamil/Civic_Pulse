import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders the CivicPulse header', () => {
    render(<App />);
    expect(screen.getByText('CivicPulse')).toBeInTheDocument();
  });

  it('renders navigation tabs', () => {
    render(<App />);
    expect(screen.getByText('📝 Submit')).toBeInTheDocument();
    expect(screen.getByText('📋 Dashboard')).toBeInTheDocument();
    expect(screen.getByText('📊 Stats')).toBeInTheDocument();
  });

  it('shows submit page by default', () => {
    render(<App />);
    expect(screen.getByText('📝 Submit a Complaint')).toBeInTheDocument();
  });

  it('has unique IDs on interactive elements', () => {
    render(<App />);
    expect(document.getElementById('nav-submit')).not.toBeNull();
    expect(document.getElementById('nav-dashboard')).not.toBeNull();
    expect(document.getElementById('nav-stats')).not.toBeNull();
  });
});

describe('SubmitPage', () => {
  it('renders the complaint form fields', () => {
    render(<App />);
    expect(screen.getByLabelText(/Complaint Details/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Contact/i)).toBeInTheDocument();
  });
});
