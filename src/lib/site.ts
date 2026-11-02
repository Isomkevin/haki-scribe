/** Public site identity for agents, SEO, and trust pages. */

export const SITE_ORIGIN = "https://hakiscribe.hakichain.com";

export const SITE_CONTACT = {
  organization: "HakiChain",
  product: "HakiScribe",
  studio: "Nairobi, Kenya",
  /** Primary public channel until a dedicated inbox is published. */
  web: "https://hakichain.com",
  productUrl: SITE_ORIGIN,
  github: "https://github.com/Isomkevin/haki-scribe",
} as const;

export function absoluteUrl(path = "/"): string {
  if (!path || path === "/") return `${SITE_ORIGIN}/`;
  return `${SITE_ORIGIN}${path.startsWith("/") ? path : `/${path}`}`;
}
