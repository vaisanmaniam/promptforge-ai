import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RepairPage } from '../pages/RepairPage';

describe('RepairPage', () => {
  it('renders page title, diagnostic indicators, and preset defect scenarios', () => {
    render(<RepairPage />);

    expect(screen.getByText('Failure-Guided Automated Code Repair')).toBeInTheDocument();
    expect(screen.getByText('Rule Engine:')).toBeInTheDocument();
    expect(screen.getByText('Sandbox:')).toBeInTheDocument();
    expect(screen.getByText('Arithmetic Operator Defect')).toBeInTheDocument();
    expect(screen.getByText('Off-By-One Boundary Defect')).toBeInTheDocument();
    expect(screen.getByText('KeyError Unhandled Exception')).toBeInTheDocument();
  });

  it('renders primary workflow controls and studio sections', () => {
    render(<RepairPage />);

    expect(screen.getByText(/1\. Load Defect Scenario & Run Diagnosis/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Ingest & Diagnose/i })).toBeInTheDocument();
    expect(screen.getByText(/2\. Diagnosed Failures/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Repair Proposal Studio/i)).toBeInTheDocument();
  });
});
