import { describe, expect, it } from "vitest";
import {
  homepageMarkdown,
  markdownForPath,
  notFoundMarkdown,
} from "./agent-markdown";

describe("agent markdown bodies", () => {
  it("serves nonempty homepage markdown with agent links", () => {
    const body = homepageMarkdown();
    expect(body.length).toBeGreaterThan(100);
    expect(body).toContain("# HakiScribe");
    expect(body).toContain("/llms.txt");
    expect(body).toContain("/sitemap.xml");
  });

  it("builds a 404 markdown body with recovery links", () => {
    const body = notFoundMarkdown("/__ora-404-probe");
    expect(body.length).toBeGreaterThanOrEqual(20);
    expect(body).toContain("not found");
    expect(body).toContain("/llms.txt");
    expect(body).toContain("/sitemap.xml");
  });

  it("resolves markdown for known public paths", () => {
    expect(markdownForPath("/")).toContain("# HakiScribe");
    expect(markdownForPath("/about")).toContain("# About");
    expect(markdownForPath("/contact")).toContain("# Contact");
    expect(markdownForPath("/privacy")).toContain("# Privacy");
    expect(markdownForPath("/new")).toContain("# Start a private");
    expect(markdownForPath("/nope")).toBeNull();
  });
});
