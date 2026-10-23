import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RegressionPage } from "../pages/RegressionPage";

describe("RegressionPage", () => {
  it("renders page title, fallback telemetry indicator, and preset scenarios", () => {
    render(<RegressionPage />);

    expect(
      screen.getByText("Predictive Regression Intelligence")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/DETERMINISTIC FALLBACK/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText("Modify Calculator add()")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Drift in LRU Eviction")
    ).toBeInTheDocument();
  });

  it("renders strategy controls and action buttons", () => {
    render(<RegressionPage />);

    expect(screen.getByText("Change Specification")).toBeInTheDocument();
    expect(screen.getByText("Prioritization Strategy")).toBeInTheDocument();
    expect(screen.getByText("Analyze & Prioritize Tests")).toBeInTheDocument();
    expect(screen.getByText("Train Pipeline (Synthetic Test)")).toBeInTheDocument();
  });
});
