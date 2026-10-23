import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RequirementsPage } from "../pages/RequirementsPage";

describe("RequirementsPage", () => {
  it("renders page title, preset buttons, and extraction action buttons", () => {
    render(<RequirementsPage />);

    expect(
      screen.getByText("Requirement Intelligence & Traceability Engine")
    ).toBeInTheDocument();
    expect(screen.getByText("Phase 3 Active")).toBeInTheDocument();
    expect(screen.getByText("Extract Requirements")).toBeInTheDocument();
    expect(screen.getByText("Save Specification")).toBeInTheDocument();
  });

  it("updates prompt textarea when clicking preset buttons", () => {
    render(<RequirementsPage />);

    const presetBtn = screen.getByText("Thread-Safe LRU Cache in Python");
    fireEvent.click(presetBtn);

    const textarea = screen.getByPlaceholderText(
      /Describe the software component/i
    ) as HTMLTextAreaElement;
    expect(textarea.value).toContain("thread-safe LRU cache");
  });
});
