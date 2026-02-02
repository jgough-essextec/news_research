import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Create hoisted mocks
const { mockSignIn, mockUseSession, mockPush } = vi.hoisted(() => ({
  mockSignIn: vi.fn(),
  mockUseSession: vi.fn(),
  mockPush: vi.fn(),
}));

// Mock next-auth/react
vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => mockSignIn(...args),
  useSession: () => mockUseSession(),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

// Import after mocks
import LoginPage from "../app/login/page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form when unauthenticated", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    render(<LoginPage />);

    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(screen.getByText("Continue with Google")).toBeInTheDocument();
  });

  it("shows loading state while checking session", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "loading",
    });

    render(<LoginPage />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("redirects authenticated users to dashboard", async () => {
    mockUseSession.mockReturnValue({
      data: { user: { name: "Test User" } },
      status: "authenticated",
    });

    render(<LoginPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("calls signIn with Google provider when button is clicked", async () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    render(<LoginPage />);

    const user = userEvent.setup();
    await user.click(screen.getByText("Continue with Google"));

    expect(mockSignIn).toHaveBeenCalledWith("google", {
      callbackUrl: "/dashboard",
    });
  });
});
