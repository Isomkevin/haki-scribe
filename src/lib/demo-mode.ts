/**
 * Known demo-seed titles/matters from hakiscribe-backend demo_catalog.
 * Used to hide seeded desk content when "Use Demo Data" is off.
 */
export const DEMO_SESSION_TITLES = [
  "Client meeting — Wanjiru Holdings, defective works at Kilimani site",
  "Voice memo — Wanjiru Holdings, Kilimani remedial works follow-up",
  "Court proceeding — Employment & Labour Relations Court, Otieno termination",
  "Client briefing — Otieno, ELRC directions after mention",
  "Client call — Mombasa Coastal Sacco, defaulted loan recovery strategy",
  "Client call — Coastal Sacco, Nyali statutory notice plan",
  "Intake — new client, land succession dispute in Kiambu",
  "Follow-up intake — Githunguri succession, revocation advice",
  "Case conference — Barclays vs. Apex Logistics, facility default and charge enforcement",
  "Client meeting — Karanja & Sons, commercial lease dispute at Westlands",
  "Site briefing — Karanja & Sons, Westlands distress after lock-out",
  "Court proceeding — Milimani Commercial Court, Riverside Properties injunction application",
  "Court proceeding — Milimani Commercial Court, Wanjiru Holdings lease arrears",
  "Client intake — Bello Trading, Kano warehouse lease dispute",
  "Client call — Adeyemi & Co, Lagos employment notice review",
  "Mention notes — Dlamini, Johannesburg eviction defence",
  // Legacy / alternate titles that may still exist on older instances
  "Sahara multilingual demo — Milimani court hearing (EN–SW code-switch)",
  "Sahara refine — Wanjiru Holdings site memo (EN–SW)",
] as const;

export const DEMO_MATTER_NAMES = [
  "Wanjiru Holdings v. Sarova Contractors — construction defect",
  "Otieno — employment termination claim",
  "Coastal Sacco — loan recovery portfolio",
  "Barclays vs. Apex Logistics",
  "Barclays vs. Apex Logistics — facility default",
  "Estate of the late Njoroge Kamau — succession",
  "Karanja & Sons v. Riverside Properties — irregular distress",
  "Wanjiru Holdings Ltd v. Kamau Enterprises Ltd — lease arrears (Milimani CS 204/2026)",
  "Bello Trading v. Northern Logistics — warehouse lease (Kano)",
  "Adeyemi — wrongful dismissal claim (Lagos)",
  "Dlamini — residential eviction defence (Johannesburg)",
] as const;

export const DEMO_CLIENT_NAMES = [
  "Wanjiru Holdings Ltd",
  "Achieng' Otieno",
  "Mombasa Coastal Sacco",
  "Barclays",
  "Apex Logistics (EA) Limited",
  "Githunguri Family Estate",
  "Karanja & Sons Ltd",
  "Kamau Enterprises Ltd",
  "Bello Trading Ltd",
  "Adeyemi & Co",
  "Thandi Dlamini",
] as const;

const demoTitleSet = new Set<string>(DEMO_SESSION_TITLES);
const demoMatterSet = new Set<string>(DEMO_MATTER_NAMES);
const demoClientSet = new Set<string>(DEMO_CLIENT_NAMES);

export function isDemoSessionTitle(title: string | null | undefined): boolean {
  if (!title) return false;
  return demoTitleSet.has(title.trim());
}

export function isDemoMatterName(name: string | null | undefined): boolean {
  if (!name) return false;
  return demoMatterSet.has(name.trim());
}

export function isDemoClientName(name: string | null | undefined): boolean {
  if (!name) return false;
  return demoClientSet.has(name.trim());
}

export function filterDemoSessions<T extends { title: string }>(items: T[], includeDemo: boolean): T[] {
  if (includeDemo) return items;
  return items.filter((item) => !isDemoSessionTitle(item.title));
}

export function filterDemoMatters<T extends { matter_name: string; client_name?: string }>(
  items: T[],
  includeDemo: boolean,
): T[] {
  if (includeDemo) return items;
  return items.filter(
    (item) => !isDemoMatterName(item.matter_name) && !isDemoClientName(item.client_name),
  );
}

export function filterDemoContacts<T extends { name: string; matter_id?: string | null }>(
  items: T[],
  includeDemo: boolean,
  demoMatterIds?: Set<string>,
): T[] {
  if (includeDemo) return items;
  return items.filter((item) => {
    if (isDemoClientName(item.name)) return false;
    if (item.matter_id && demoMatterIds?.has(item.matter_id)) return false;
    return true;
  });
}
