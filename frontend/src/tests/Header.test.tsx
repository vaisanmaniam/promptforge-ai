import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "../components/layout/Header";

describe("Header", () => {
  it("renders branding and tagline", () => {
    render(
      <Header
        health={null}
        isBackendConnected={false}
        isLoading={false}
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByText("PromptForge AI")).toBeInTheDocument();
    expect(screen.getByText("From Natural Language to Verified Software")).toBeInTheDocument();
    expect(screen.getByText("Backend Offline")).toBeInTheDocument();
  });

  it("displays backend online badge when connected", () => {
    const mockHealth = {
      status: "healthy",
      version: "0.1.0",
      environment: "development",
      timestamp: "2026-10-09T00:00:00Z",
    };

    render(
      <Header
        health={mockHealth}
        isBackendConnected={true}
        isLoading={false}
        onRefresh={vi.fn()}
      />
    );

    expect(screen.getByText("Backend Online")).toBeInTheDocument();
    expect(screen.getByText(/v0\.1\.0/)).toBeInTheDocument();
  });
});
