import { describe, it, expect } from "vitest";
import { config } from "../middleware";

describe("Middleware Configuration", () => {
  it("has matcher for dashboard routes", () => {
    expect(config.matcher).toContain("/dashboard/:path*");
  });

  it("only matches dashboard paths", () => {
    // The matcher should only include dashboard routes
    expect(config.matcher).toHaveLength(1);
    expect(config.matcher[0]).toBe("/dashboard/:path*");
  });

  it("does not match public routes", () => {
    // These routes should NOT be in the matcher
    expect(config.matcher).not.toContain("/");
    expect(config.matcher).not.toContain("/login");
    expect(config.matcher).not.toContain("/api/:path*");
  });
});
