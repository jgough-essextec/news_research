import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "../app/page";

describe("Landing Page", () => {
  it("renders the title", () => {
    render(<Home />);
    expect(screen.getByText("AI News Aggregator")).toBeInTheDocument();
  });

  it("renders the description", () => {
    render(<Home />);
    expect(
      screen.getByText(/Aggregate AI news from your favorite newsletters/i)
    ).toBeInTheDocument();
  });

  it("has Get Started button that links to login", () => {
    render(<Home />);
    const getStartedLink = screen.getByRole("link", { name: /get started/i });
    expect(getStartedLink).toHaveAttribute("href", "/login");
  });

  it("does not link directly to dashboard without auth", () => {
    render(<Home />);
    const links = screen.getAllByRole("link");

    // No link should go directly to /dashboard
    links.forEach((link) => {
      expect(link).not.toHaveAttribute("href", "/dashboard");
    });
  });
});
