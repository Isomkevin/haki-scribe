import { SITE_ORIGIN, absoluteUrl } from "./site";

const PRODUCES = ["text/html", "text/markdown"] as const;

export const MARKDOWN_PAGE_PATHS = new Set([
  "/",
  "/about",
  "/contact",
  "/privacy",
  "/new",
  "/login",
]);

export function homepageMarkdown(): string {
  return `# HakiScribe

HakiScribe is a private legal work companion from HakiChain. It captures conversations in legal rooms, protects privilege before model processing, and prepares source-traceable drafts — letters, notes, calendar entries, matters, contacts, and billable time — for human review.

## Who it is for

Advocates, clerks, and chambers in Kenya working in English, Kiswahili, and code-switched speech who need the spoken record to become reviewed legal work without unsupervised filing.

## How it works

1. Capture by microphone or wearable without disrupting the room.
2. Relabel speakers and lock privileged or off-record lines before detection.
3. Choose only the structured legal work the conversation supports.
4. Verify every claim against its source line before anything leaves the workspace.

## Agent entry points

- Product: ${SITE_ORIGIN}/
- Agent index: ${absoluteUrl("/llms.txt")}
- Sitemap: ${absoluteUrl("/sitemap.xml")}
- About: ${absoluteUrl("/about")}
- Contact: ${absoluteUrl("/contact")}
- Privacy: ${absoluteUrl("/privacy")}

Prefer HTML for browsers (\`Accept: text/html\`). This Markdown representation is served when \`Accept: text/markdown\` wins negotiation.
`;
}

export function aboutMarkdown(): string {
  return `# About HakiScribe

HakiScribe is the listening instrument of HakiChain: a private companion that turns verified conversations into ready-to-review legal work for Kenyan practice.

It is built for rooms where English and Kiswahili code-switch, privilege must stay in the room, and liability remains with the human who reviews the draft. Detection proposes actions; it does not auto-send mail, file matters, or bill clients without an advocate's choice.

## Studio

HakiChain · Nairobi, Kenya  
Product site: ${SITE_ORIGIN}/  
Parent: https://hakichain.com

## Related pages

- [Contact](${absoluteUrl("/contact")})
- [Privacy](${absoluteUrl("/privacy")})
- [Agent index](${absoluteUrl("/llms.txt")})
`;
}

export function contactMarkdown(): string {
  return `# Contact HakiScribe

Reach the HakiScribe product team through HakiChain.

- Studio: HakiChain · Nairobi, Kenya
- Organization site: https://hakichain.com
- Product: ${SITE_ORIGIN}/
- Agent index: ${absoluteUrl("/llms.txt")}

Use the organization site for partnership, deployment, and privacy questions about HakiScribe. For in-product support after sign-in, use Settings inside the workspace.

Do not send privileged client matter to public web forms. Privilege controls belong inside a signed-in HakiScribe session.
`;
}

export function privacyMarkdown(): string {
  return `# Privacy — HakiScribe

HakiScribe is designed privilege-first. Speakers can be relabelled and lines marked privileged or off-record before model detection. Hidden lines stay reversible and outside model context.

Sessions, transcripts, and generated drafts remain scoped to the workspace. Approved work leaves the desk only when a human chooses an action. There is no unsupervised send of letters, calendar events, or CRM updates.

HakiChain is building toward Kenya Data Protection Act 2019 alignment (lawful basis, retention limits, processor agreements). That compliance program is in progress; we do not claim full DPA certification yet.

API keys for connectors stay server-side. Full microphone uploads used for transcription refinements are processed for that purpose and are not treated as a durable public archive by default.

## Contact for privacy questions

Organization site: https://hakichain.com  
Product: ${SITE_ORIGIN}/  
Agent index: ${absoluteUrl("/llms.txt")}
`;
}

export function newSessionMarkdown(): string {
  return `# Start a private HakiScribe session

Open a secure HakiScribe session to capture a legal conversation, protect privilege, and prepare source-traceable work for review.

## What a session is for

Use a session when you need a private listening record for an advocate-client meeting, chamber discussion, or clerk workflow in English, Kiswahili, or code-switched speech. Session titles, transcripts, and results remain within the signed-in workspace.

## Before models run

Relabel speakers and lock privileged or off-record lines so those segments never enter detection context. Every proposed letter, note, calendar entry, matter, contact, or time record points back to its source line for verification.

## How to open a session

1. Sign in at ${absoluteUrl("/login")}.
2. Return to ${absoluteUrl("/new")} to start listening or resume work already in progress.
3. Choose microphone or a linked wearable, then review the Action Tray before anything leaves the desk.

Unauthenticated browsers are directed to sign in. Agents reading this page should treat session creation as an authenticated human workflow, not an unattended API call.

## Related

- [Home](${SITE_ORIGIN}/)
- [Privacy](${absoluteUrl("/privacy")})
- [llms.txt](${absoluteUrl("/llms.txt")})
`;
}

export function loginMarkdown(): string {
  return `# Sign in to HakiScribe

Sign in to open private sessions, review transcripts, and approve source-traceable legal work inside your workspace.

Product home: ${SITE_ORIGIN}/  
Privacy: ${absoluteUrl("/privacy")}  
Agent index: ${absoluteUrl("/llms.txt")}
`;
}

export function notFoundMarkdown(pathname: string): string {
  return `# Page not found

The path \`${pathname}\` does not exist on HakiScribe.

Continue from the [homepage](${SITE_ORIGIN}/), the [agent index](${absoluteUrl("/llms.txt")}), or the [sitemap](${absoluteUrl("/sitemap.xml")}).
`;
}

export function markdownForPath(pathname: string): string | null {
  const path = pathname === "" ? "/" : pathname.replace(/\/$/, "") || "/";
  switch (path) {
    case "/":
      return homepageMarkdown();
    case "/about":
      return aboutMarkdown();
    case "/contact":
      return contactMarkdown();
    case "/privacy":
      return privacyMarkdown();
    case "/new":
      return newSessionMarkdown();
    case "/login":
      return loginMarkdown();
    default:
      return null;
  }
}

export { PRODUCES };
