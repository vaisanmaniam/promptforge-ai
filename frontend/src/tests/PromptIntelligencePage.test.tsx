import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PromptIntelligencePage } from "../pages/PromptIntelligencePage";

describe("PromptIntelligencePage", () => {
  it("renders editor, action buttons, and sample prompt buttons", () => {
    render(<PromptIntelligencePage />);

    expect(
      screen.getByText("Prompt Analysis & Optimization Studio")
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Enter a software engineering prompt/i)
    ).toBeInTheDocument();
    expect(screen.getByText("Analyze Prompt")).toBeInTheDocument();
    expect(screen.getByText("Optimize Prompt")).toBeInTheDocument();
  });

  it("loads sample prompt into textarea on click", () => {
    render(<PromptIntelligencePage />);

    const sampleBtn = screen.getByText("LRU Cache (High Quality)");
    fireEvent.click(sampleBtn);

    const textarea = screen.getByPlaceholderText(
      /Enter a software engineering prompt/i
    ) as HTMLTextAreaElement;
    expect(textarea.value).toContain("LRU cache");
  });
});
