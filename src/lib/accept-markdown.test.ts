import { describe, expect, it } from "vitest";
import { parseAccept, preferredType, prefersMarkdown, withVaryAccept } from "./accept-markdown";

describe("parseAccept", () => {
  it("parses q-values and specificity", () => {
    const entries = parseAccept("text/html;q=0.8, text/markdown, */*;q=0.1");
    expect(entries.find((e) => e.type === "text/markdown")?.q).toBe(1);
    expect(entries.find((e) => e.type === "text/html")?.q).toBe(0.8);
  });
});

describe("preferredType", () => {
  it("defaults to first produce when Accept is missing", () => {
    expect(preferredType(null, ["text/html", "text/markdown"])).toBe("text/html");
  });

  it("prefers text/markdown when it wins", () => {
    expect(
      preferredType("text/markdown, text/html;q=0.8", ["text/html", "text/markdown"]),
    ).toBe("text/markdown");
  });

  it("prefers text/html when markdown is lower q", () => {
    expect(
      preferredType("text/html, text/markdown;q=0.5", ["text/html", "text/markdown"]),
    ).toBe("text/html");
  });
});

describe("prefersMarkdown", () => {
  it("is true for Accept: text/markdown", () => {
    expect(prefersMarkdown("text/markdown")).toBe(true);
  });

  it("is false for Accept: text/html", () => {
    expect(prefersMarkdown("text/html")).toBe(false);
  });
});

describe("withVaryAccept", () => {
  it("sets Vary: Accept when missing", () => {
    const headers = withVaryAccept(new Headers());
    expect(headers.get("vary")).toBe("Accept");
  });

  it("appends Accept to an existing Vary", () => {
    const headers = withVaryAccept(new Headers({ vary: "Accept-Encoding" }));
    expect(headers.get("vary")).toBe("Accept-Encoding, Accept");
  });
});
