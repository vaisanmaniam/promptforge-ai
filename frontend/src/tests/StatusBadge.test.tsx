import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../components/ui/StatusBadge";

describe("StatusBadge", () => {
  it("renders READY status correctly", () => {
    render(<StatusBadge status="ready" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("READY");
    expect(badge).toHaveClass("text-emerald-400");
  });

  it("renders UNAVAILABLE status correctly", () => {
    render(<StatusBadge status="unavailable" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("UNAVAILABLE");
    expect(badge).toHaveClass("text-rose-400");
  });

  it("renders NOT_CONFIGURED status correctly", () => {
    render(<StatusBadge status="not_configured" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("NOT CONFIGURED");
    expect(badge).toHaveClass("text-slate-400");
  });

  it("renders NOT_TRAINED baseline status correctly", () => {
    render(<StatusBadge status="not_trained" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toHaveTextContent("NOT TRAINED (BASELINE)");
    expect(badge).toHaveClass("text-amber-400");
  });
});
