import { SITE_CONTACT, SITE_ORIGIN } from "./site";

/** Plain-text bodies used by trust pages and static readiness tests (≥500 chars each). */

export const ABOUT_COPY = {
  title: "About HakiScribe",
  eyebrow: "HakiChain listening instrument",
  lead:
    "HakiScribe is a private legal work companion for Kenyan advocates, clerks, and chambers. It captures what is said in the room, protects privilege before models run, and prepares source-traceable drafts for human review.",
  sections: [
    {
      heading: "Why it exists",
      body: `Legal rooms already carry the hard work of listening. What often fails afterward is the handoff into letters, matters, notes, calendar entries, contacts, and billable time — especially when English and Kiswahili code-switch in the same conversation. HakiScribe keeps the spoken record inside a workspace, proposes structured work grounded in that record, and never treats unsupervised filing as success.`,
    },
    {
      heading: "Human review stays required",
      body: `Detection proposes; advocates decide. Privilege and off-record lines can be locked before processing so those segments stay outside model context. Every claim in the Action Tray points back to a source line so a reviewer can verify before anything leaves the desk. Liability remains with the human who was always going to carry it.`,
    },
    {
      heading: "Studio",
      body: `${SITE_CONTACT.product} is built as a listening instrument of ${SITE_CONTACT.organization}, based in ${SITE_CONTACT.studio}. Parent organization: ${SITE_CONTACT.web}. Product: ${SITE_ORIGIN}/.`,
    },
  ],
} as const;

export const CONTACT_COPY = {
  title: "Contact HakiScribe",
  eyebrow: "Reach the studio",
  lead:
    "Contact HakiChain for HakiScribe product questions, partnership, deployment, and privacy inquiries. Do not send privileged client matter through public web channels.",
  sections: [
    {
      heading: "Organization",
      body: `${SITE_CONTACT.organization} · ${SITE_CONTACT.studio}. Primary public channel: ${SITE_CONTACT.web}. Product site: ${SITE_CONTACT.productUrl}. Use the organization site to reach the team that operates HakiScribe. After you have a workspace account, in-product Settings is the right place for day-to-day account and connector questions.`,
    },
    {
      heading: "What to include",
      body: `When you write, say whether your note is about product access, a deployment environment, a privacy question, or a connector. Do not paste transcripts, client names, or privileged segments into public mail or web forms. Privilege controls belong inside a signed-in HakiScribe session where speakers can be relabelled and off-record lines locked before detection.`,
    },
    {
      heading: "Agents and documentation",
      body: `Machine-readable entry points live at ${SITE_ORIGIN}/llms.txt and ${SITE_ORIGIN}/sitemap.xml. Public trust pages are /about, /contact, and /privacy. Session creation at /new requires human sign-in; agents should not treat unattended session APIs as available from this contact page.`,
    },
  ],
} as const;

export const PRIVACY_COPY = {
  title: "Privacy at HakiScribe",
  eyebrow: "Privilege before processing",
  lead:
    "HakiScribe is built so privilege can stay in the room. Hidden lines remain reversible and outside model context. Approved work leaves the workspace only when a human chooses an action.",
  sections: [
    {
      heading: "Privilege and off-record speech",
      body: `Before detection runs, you can relabel speakers and mark privileged or off-record lines. Those segments are excluded from model context while remaining visible to the signed-in user for review. This control is core product behavior, not a marketing claim: drafts and proposed actions should never be grounded in lines you locked away.`,
    },
    {
      heading: "Workspace scope and human approval",
      body: `Sessions, transcripts, and generated drafts stay scoped to the workspace. The Action Tray is selective: letters, calendar events, matters, contacts, and time entries require explicit human choice. There is no unsupervised send. Connector credentials remain server-side; the UI surfaces masked hints only.`,
    },
    {
      heading: "Kenya Data Protection Act alignment",
      body: `${SITE_CONTACT.organization} is building toward Kenya Data Protection Act 2019 alignment — lawful basis, retention limits, and processor agreements. That compliance program is in progress. We do not claim full DPA certification yet. For privacy questions about HakiScribe, start at ${SITE_CONTACT.web} or the product contact page at ${SITE_ORIGIN}/contact.`,
    },
  ],
} as const;

export function trustPlainText(
  copy: typeof ABOUT_COPY | typeof CONTACT_COPY | typeof PRIVACY_COPY,
): string {
  const parts = [copy.title, copy.lead, ...copy.sections.map((s) => `${s.heading}\n${s.body}`)];
  return parts.join("\n\n");
}
