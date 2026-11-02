import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ABOUT_COPY,
  CONTACT_COPY,
  PRIVACY_COPY,
  trustPlainText,
} from "./trust-pages";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

describe("static agent discovery files", () => {
  it("publishes llms.txt with when-to-use guidance", () => {
    const body = readFileSync(resolve(root, "public/llms.txt"), "utf8");
    expect(body.length).toBeGreaterThanOrEqual(100);
    expect(body.toLowerCase()).toContain("when to use");
    expect(body).toContain("# HakiScribe");
    expect(body).toContain("https://hakiscribe.hakichain.com/");
  });

  it("publishes sitemap.xml with lastmod dates", () => {
    const body = readFileSync(resolve(root, "public/sitemap.xml"), "utf8");
    expect(body).toContain("<urlset");
    expect(body).toContain("<lastmod>");
    expect(body).toContain("https://hakiscribe.hakichain.com/");
    expect(body).toContain("/about");
    expect(body).toContain("/contact");
    expect(body).toContain("/privacy");
  });

  it("declares Sitemap in robots.txt", () => {
    const body = readFileSync(resolve(root, "public/robots.txt"), "utf8");
    expect(body).toContain("Sitemap: https://hakiscribe.hakichain.com/sitemap.xml");
  });
});

describe("trust page copy", () => {
  it.each([
    ["about", ABOUT_COPY],
    ["contact", CONTACT_COPY],
    ["privacy", PRIVACY_COPY],
  ] as const)("%s has at least 500 characters", (_name, copy) => {
    expect(trustPlainText(copy).length).toBeGreaterThanOrEqual(500);
  });
});
