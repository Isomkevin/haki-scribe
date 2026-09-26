import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Mail, Phone, Plus, Search, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDemoMode } from "@/hooks/use-demo-mode";
import { filterDemoContacts, filterDemoMatters } from "@/lib/demo-mode";
import { hakiApi, friendlyErrorMessage, type Contact, type Matter } from "@/lib/hakiscribe";
import { PageShell, WorkspaceFooter } from "./shell";

const ALL = "__all";
const NONE = "__none";

export function field(contact: Contact, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = contact.updates?.[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return null;
}

const SHOWN_KEYS = new Set(["role", "email", "phone", "phone_number", "organisation", "organization", "company", "title", "source"]);

function extraDetails(contact: Contact): [string, string][] {
  return Object.entries(contact.updates ?? {})
    .filter(([key, value]) => !SHOWN_KEYS.has(key) && (typeof value === "string" || typeof value === "number") && String(value).trim())
    .map(([key, value]) => [key.replace(/[_-]/g, " "), String(value)]);
}

export function ContactDirectory({ quickAdd = false }: { quickAdd?: boolean }) {
  const { enabled: demo } = useDemoMode();
  const contactsQ = useQuery({ queryKey: ["contacts"], queryFn: hakiApi.listContacts, refetchInterval: 20_000, retry: false });
  const mattersQ = useQuery({ queryKey: ["matters"], queryFn: hakiApi.listMatters, refetchInterval: 20_000, retry: false });
  const [q, setQ] = useState("");
  const [matterFilter, setMatterFilter] = useState(ALL);
  const [roleFilter, setRoleFilter] = useState(ALL);

  const matters = filterDemoMatters(mattersQ.data ?? [], demo);
  const demoMatterIds = useMemo(
    () => new Set((mattersQ.data ?? []).filter((m) => !matters.includes(m)).map((m) => m.id)),
    [mattersQ.data, matters],
  );
  const contacts = filterDemoContacts(contactsQ.data ?? [], demo, demoMatterIds);
  const matterById = new Map(matters.map((m) => [m.id, m]));
  const roles = Array.from(new Set(contacts.map((c) => field(c, "role")).filter((r): r is string => Boolean(r)))).sort();

  const needle = q.trim().toLowerCase();
  const visible = contacts
    .filter((c) => {
      if (matterFilter === NONE && c.matter_id) return false;
      if (matterFilter !== ALL && matterFilter !== NONE && c.matter_id !== matterFilter) return false;
      if (roleFilter !== ALL && field(c, "role") !== roleFilter) return false;
      if (!needle) return true;
      const matter = c.matter_id ? matterById.get(c.matter_id) : undefined;
      const hay = [c.name, matter?.matter_name, matter?.client_name, ...Object.values(c.updates ?? {}).map(String)]
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="grid gap-5">
      {quickAdd ? <QuickAdd matters={matters} /> : null}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[12rem] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, matter, email, phone…"
            className="pl-8"
            aria-label="Search contacts"
          />
        </div>
        <Select value={matterFilter} onValueChange={setMatterFilter}>
          <SelectTrigger className="w-[11rem]" aria-label="Filter by matter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All matters</SelectItem>
            <SelectItem value={NONE}>No matter</SelectItem>
            {matters.map((m) => (
              <SelectItem key={m.id} value={m.id}>{m.matter_name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-[9rem]" aria-label="Filter by role"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All roles</SelectItem>
            {roles.map((r) => (
              <SelectItem key={r} value={r} className="capitalize">{r}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <p className="text-xs text-muted-foreground">
        {visible.length} of {contacts.length} contacts across {matters.length} matters
      </p>

      {contactsQ.isError ? (
        <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {friendlyErrorMessage(contactsQ.error, "Contacts could not be loaded. Confirm the HakiScribe service is running.")}
        </p>
      ) : visible.length === 0 && !contactsQ.isLoading ? (
        <p className="rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          {contacts.length === 0
            ? "No contacts yet. They appear when a session creates a matter or CRM entry, or when you add one."
            : "No contacts match your search."}
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {visible.map((c) => (
            <ContactCard key={c.id} contact={c} matter={c.matter_id ? matterById.get(c.matter_id) : undefined} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ContactCard({ contact, matter }: { contact: Contact; matter?: Matter | undefined }) {
  const role = field(contact, "role", "title");
  const email = field(contact, "email");
  const phone = field(contact, "phone", "phone_number");
  const org = field(contact, "organisation", "organization", "company");
  const extras = extraDetails(contact);
  const sessionId = contact.session_id ?? matter?.session_ids?.[0] ?? null;
  return (
    <li className="min-w-0 rounded-lg border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
          <UserRound className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <Link
            to="/contacts/$contactId"
            params={{ contactId: contact.id }}
            className="block truncate font-serif text-base font-semibold underline-offset-4 hover:text-primary hover:underline"
          >
            {contact.name}
          </Link>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {role ? <Badge variant="secondary" className="text-[11px] capitalize">{role}</Badge> : null}
            {org ? <Badge variant="outline" className="text-[11px]">{org}</Badge> : null}
          </div>
        </div>
      </div>
      <div className="mt-3 grid gap-1 text-sm">
        {email ? (
          <a href={`mailto:${email}`} className="flex min-w-0 items-center gap-2 text-primary underline-offset-4 hover:underline">
            <Mail className="size-3.5 shrink-0" /><span className="truncate">{email}</span>
          </a>
        ) : null}
        {phone ? (
          <a href={`tel:${phone}`} className="flex items-center gap-2 text-primary underline-offset-4 hover:underline">
            <Phone className="size-3.5 shrink-0" />{phone}
          </a>
        ) : null}
        {!email && !phone ? <p className="text-xs text-muted-foreground">No email or phone on the record.</p> : null}
        {extras.map(([k, v]) => (
          <p key={k} className="text-xs text-muted-foreground"><span className="capitalize">{k}</span>: {v}</p>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3 text-xs">
        <span className="text-muted-foreground">Matter:</span>
        {matter && sessionId ? (
          <Link to="/sessions/$sessionId" params={{ sessionId }} search={{ fresh: false }} className="font-medium text-primary underline-offset-4 hover:underline">
            {matter.matter_name}
          </Link>
        ) : matter ? (
          <span className="font-medium">{matter.matter_name}</span>
        ) : (
          <span className="text-muted-foreground">Not linked</span>
        )}
        <Link to="/contacts/$contactId" params={{ contactId: contact.id }} className="ml-auto font-medium text-primary underline-offset-4 hover:underline">
          Open profile{(contact.session_ids?.length ?? 0) > 0 ? ` · ${contact.session_ids!.length} session${contact.session_ids!.length === 1 ? "" : "s"}` : ""}
        </Link>
        {!matter && sessionId ? (
          <Link to="/sessions/$sessionId" params={{ sessionId }} search={{ fresh: false }} className="text-primary underline-offset-4 hover:underline">
            Open session
          </Link>
        ) : null}
      </div>
    </li>
  );
}

function QuickAdd({ matters }: { matters: Matter[] }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [matterId, setMatterId] = useState(NONE);
  const [sessionId, setSessionId] = useState(NONE);
  const sessionsQ = useQuery({ queryKey: ["sessions", "contact-source"], queryFn: () => hakiApi.listSessions({ includeDemo: true }), retry: false });
  const add = useMutation({
    mutationFn: () => {
      const updates: Record<string, unknown> = { source: "contacts_directory" };
      if (role.trim()) updates["role"] = role.trim();
      if (email.trim()) updates["email"] = email.trim();
      if (phone.trim()) updates["phone"] = phone.trim();
      const body: { name: string; updates: Record<string, unknown>; matter_id?: string; session_id?: string } = { name: name.trim(), updates };
      if (matterId !== NONE) body.matter_id = matterId;
      if (sessionId !== NONE) body.session_id = sessionId;
      return hakiApi.createContact(body);
    },
    onSuccess: () => {
      toast.success(`${name.trim()} added`);
      setName(""); setRole(""); setEmail(""); setPhone("");
      void qc.invalidateQueries({ queryKey: ["contacts"] });
      void qc.invalidateQueries({ queryKey: ["matters"] });
      void qc.invalidateQueries({ queryKey: ["session"] });
    },
    onError: (e) => toast.error(friendlyErrorMessage(e, "The contact could not be saved.")),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (name.trim()) add.mutate();
  };
  return (
    <form onSubmit={submit} className="grid gap-3 rounded-lg border border-border bg-card p-4 sm:grid-cols-6 sm:items-end">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground sm:col-span-6">Quick add</p>
      <div className="grid gap-1.5 sm:col-span-2"><Label htmlFor="qa-name">Name</Label><Input id="qa-name" value={name} onChange={(e) => setName(e.target.value)} required /></div>
      <div className="grid gap-1.5 sm:col-span-2"><Label htmlFor="qa-role">Role</Label><Input id="qa-role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Client, witness, counsel…" /></div>
      <div className="grid gap-1.5 sm:col-span-2">
        <Label>Matter</Label>
        <Select value={matterId} onValueChange={setMatterId}>
          <SelectTrigger aria-label="Matter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={NONE}>No matter</SelectItem>
            {matters.map((m) => <SelectItem key={m.id} value={m.id}>{m.matter_name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="grid gap-1.5 sm:col-span-2"><Label htmlFor="qa-email">Email</Label><Input id="qa-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
      <div className="grid gap-1.5 sm:col-span-2"><Label htmlFor="qa-phone">Phone</Label><Input id="qa-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
      <div className="grid gap-1.5 sm:col-span-4">
        <Label>Session source</Label>
        <Select value={sessionId} onValueChange={setSessionId}>
          <SelectTrigger aria-label="Session source"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value={NONE}>Not from a session</SelectItem>
            {(sessionsQ.data ?? []).map((s) => <SelectItem key={s.id} value={s.id}>{s.title}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" className="sm:col-span-2" disabled={!name.trim() || add.isPending}>
        <Plus className="size-4" />{add.isPending ? "Saving…" : "Add contact"}
      </Button>
    </form>
  );
}

export function ContactsPage() {
  return (
    <PageShell back>
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        <header className="mb-7 border-b border-border pb-7">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Contacts</p>
          <h1 className="mt-2 font-serif text-3xl font-semibold leading-tight sm:text-4xl">Everyone across your matters</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Clients, witnesses, counsel and counterparts gathered from every session. Anyone named as a speaker in a mic or Omi recording is added automatically; open a person to see their full record or edit their details.
          </p>
        </header>
        <ContactDirectory quickAdd />
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}
