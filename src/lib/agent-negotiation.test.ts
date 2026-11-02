import { describe, expect, it } from "vitest";
import { finalizeAgentResponse, negotiateAgentRequest } from "./agent-negotiation";

describe("negotiateAgentRequest", () => {
  it("returns markdown for the homepage when Accept prefers markdown", async () => {
    const request = new Request("https://hakiscribe.hakichain.com/", {
      headers: { Accept: "text/markdown" },
    });
    const response = negotiateAgentRequest(request);
    expect(response).not.toBeNull();
    expect(response!.status).toBe(200);
    expect(response!.headers.get("content-type")).toContain("text/markdown");
    expect(response!.headers.get("vary")?.toLowerCase()).toContain("accept");
    const body = await response!.text();
    expect(body.length).toBeGreaterThan(0);
    expect(body).toContain("# HakiScribe");
  });

  it("does not short-circuit HTML Accept for the homepage", () => {
    const request = new Request("https://hakiscribe.hakichain.com/", {
      headers: { Accept: "text/html" },
    });
    expect(negotiateAgentRequest(request)).toBeNull();
  });

  it("returns markdown 404 for unknown paths preferring markdown", async () => {
    const request = new Request("https://hakiscribe.hakichain.com/__ora-404-probe", {
      headers: { Accept: "text/markdown" },
    });
    const response = negotiateAgentRequest(request);
    expect(response).not.toBeNull();
    expect(response!.status).toBe(404);
    expect(response!.headers.get("content-type")).toContain("text/markdown");
    const body = await response!.text();
    expect(body.length).toBeGreaterThanOrEqual(20);
    expect(body).toContain("/llms.txt");
  });
});

describe("finalizeAgentResponse", () => {
  it("upgrades HTML 404 to markdown when Accept prefers markdown", async () => {
    const request = new Request("https://hakiscribe.hakichain.com/missing-page", {
      headers: { Accept: "text/markdown" },
    });
    const response = finalizeAgentResponse(
      request,
      new Response("<html>not found</html>", {
        status: 404,
        headers: { "content-type": "text/html" },
      }),
    );
    expect(response.status).toBe(404);
    expect(response.headers.get("content-type")).toContain("text/markdown");
    expect(await response.text()).toContain("Page not found");
  });

  it("adds Vary: Accept on HTML homepage responses", () => {
    const request = new Request("https://hakiscribe.hakichain.com/", {
      headers: { Accept: "text/html" },
    });
    const response = finalizeAgentResponse(
      request,
      new Response("<html>ok</html>", {
        status: 200,
        headers: { "content-type": "text/html" },
      }),
    );
    expect(response.headers.get("vary")?.toLowerCase()).toContain("accept");
  });
});
