import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerificationPage } from "../pages/VerificationPage";

describe("VerificationPage", () => {
  it("renders page title, Phase 4 badge, and upload actions", () => {
    render(<VerificationPage />);

    expect(
      screen.getByText("Code Evidence & Automated Verification")
    ).toBeInTheDocument();
    expect(screen.getByText("Phase 4 Active")).toBeInTheDocument();
    expect(screen.getByText("Upload ZIP")).toBeInTheDocument();
  });

  it("renders sample presets buttons", () => {
    render(<VerificationPage />);

    expect(screen.getByText("LRU Preset")).toBeInTheDocument();
    expect(screen.getByText("User Preset")).toBeInTheDocument();
  });
});
