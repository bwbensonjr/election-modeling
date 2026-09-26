import { describe, expect, it } from "vitest";
import { renderDistribution } from "./chart";

describe("distribution chart", () => {
  it("renders paired series and a zero marker", () => {
    const container = document.createElement("div");
    renderDistribution(container, [-2, -1, 0, 1], [-1, 0, 1, 2]);
    expect(container.querySelectorAll(".density-line")).toHaveLength(2);
    expect(container.querySelector(".zero-line")).not.toBeNull();
    expect(container.querySelectorAll(".tick-label").length).toBeGreaterThan(0);
  });
});
