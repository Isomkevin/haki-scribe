import {
  MARKDOWN_PAGE_PATHS,
  markdownForPath,
  notFoundMarkdown,
  PRODUCES,
} from "./agent-markdown";
import { markdownResponse, preferredType, prefersMarkdown, withVaryAccept } from "./accept-markdown";

function normalizePath(pathname: string): string {
  if (!pathname || pathname === "/") return "/";
  const trimmed = pathname.replace(/\/$/, "");
  return trimmed || "/";
}

/**
 * Handle Accept: text/markdown short-circuit and 404 Markdown upgrades.
 * Returns a Response when negotiation fully resolves the request; otherwise null
 * so the caller can continue to TanStack Start (optionally wrapping HTML with Vary).
 */
export function negotiateAgentRequest(request: Request): Response | null {
  if (request.method !== "GET" && request.method !== "HEAD") return null;

  const url = new URL(request.url);
  const path = normalizePath(url.pathname);
  const accept = request.headers.get("accept");
  const chosen = preferredType(accept, [...PRODUCES]);

  if (chosen === "text/markdown") {
    const body = markdownForPath(path);
    if (body) {
      return markdownResponse(request.method === "HEAD" ? "" : body);
    }
    // Unknown path preferring markdown: answer as agent-friendly 404 without SSR.
    if (!MARKDOWN_PAGE_PATHS.has(path) && !isLikelyStaticAsset(path)) {
      return markdownResponse(request.method === "HEAD" ? "" : notFoundMarkdown(path), {
        status: 404,
      });
    }
  }

  return null;
}

export function finalizeAgentResponse(request: Request, response: Response): Response {
  const url = new URL(request.url);
  const path = normalizePath(url.pathname);
  const accept = request.headers.get("accept");

  if (prefersMarkdown(accept) && (response.status === 404 || response.status === 410)) {
    return markdownResponse(notFoundMarkdown(path), { status: response.status });
  }

  if (MARKDOWN_PAGE_PATHS.has(path) && preferredType(accept, [...PRODUCES]) !== null) {
    const headers = withVaryAccept(response.headers);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  }

  return response;
}

function isLikelyStaticAsset(path: string): boolean {
  return /\.[a-z0-9]{2,8}$/i.test(path) || path.startsWith("/.");
}
