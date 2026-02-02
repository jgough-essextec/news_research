import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// Create hoisted mocks
const { mockSignOut, mockUseSession, mockPush } = vi.hoisted(() => ({
  mockSignOut: vi.fn(),
  mockUseSession: vi.fn(),
  mockPush: vi.fn(),
}));

// Mock next-auth/react
vi.mock("next-auth/react", () => ({
  signOut: mockSignOut,
  useSession: () => mockUseSession(),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => "/dashboard",
}));

// Import after mocks
import DashboardLayout from "../app/dashboard/layout";

describe("DashboardLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state while checking session", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "loading",
    });

    render(
      <DashboardLayout>
        <div>Dashboard Content</div>
      </DashboardLayout>
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Content")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to login", async () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    render(
      <DashboardLayout>
        <div>Dashboard Content</div>
      </DashboardLayout>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        "/login?callbackUrl=%2Fdashboard"
      );
    });
  });

  it("renders dashboard content for authenticated users", () => {
    mockUseSession.mockReturnValue({
      data: {
        user: {
          name: "Test User",
          email: "test@example.com",
          image: "https://example.com/avatar.jpg",
        },
      },
      status: "authenticated",
    });

    render(
      <DashboardLayout>
        <div>Dashboard Content</div>
      </DashboardLayout>
    );

    expect(screen.getByText("Dashboard Content")).toBeInTheDocument();
    expect(screen.getByText("AI News")).toBeInTheDocument();
  });

  it("renders navigation links for authenticated users", () => {
    mockUseSession.mockReturnValue({
      data: {
        user: {
          name: "Test User",
          email: "test@example.com",
        },
      },
      status: "authenticated",
    });

    render(
      <DashboardLayout>
        <div>Content</div>
      </DashboardLayout>
    );

    // Use getAllByRole to find navigation links
    const navLinks = screen.getAllByRole("link");
    const navLinkTexts = navLinks.map((link) => link.textContent);

    expect(navLinkTexts).toContain("Dashboard");
    expect(navLinkTexts).toContain("Emails");
    expect(navLinkTexts).toContain("Articles");
    expect(navLinkTexts).toContain("Clusters");
    expect(navLinkTexts).toContain("Posts");
  });

  it("does not render content when unauthenticated", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
    });

    const { container } = render(
      <DashboardLayout>
        <div>Dashboard Content</div>
      </DashboardLayout>
    );

    // Should render null, so container should be empty (except for the wrapper div)
    expect(container.firstChild).toBeNull();
  });
});
