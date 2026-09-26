import { useState, type FormEvent } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { CalendarClock, ExternalLink, FileText, Mail, MapPin, Pencil, Phone, Plus, Scale, Trash2, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { hakiApi, friendlyErrorMessage, type Contact, type Matter, type SessionDetail } from "@/lib/hakiscribe";
import { PageShell, SectionHeading, SourceIcon, WorkspaceFooter } from "./shell";
import { documentOf, eventOf, formatDate, formatDay, type TrackedDocument, type TrackedEvent } from "./tracker";
import { field } from "./contacts";

const NONE = "__none";
const CORE_FIELDS: { key: string; label: string; type?: string; aliases?: string[] }[] = [
  { key: "role", label: "Role", aliases: ["title"] },
  { key: "organisation", label: "Organisation", aliases: ["organization", "company"] },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "tel", aliases: ["phone_number"] },
  { key: "address", label: "Address" },
];
const HIDDEN = new Set(["source", "notes", ...CORE_FIELDS.flatMap((f) => [f.key, ...(f.aliases ?? [])])]);

type Reason = "linked" | "matter" | "speaker" | "mentioned";
const REASON_LABEL: Record<Reason, string> = {
  linked: "Linked",
  matter: "Same matter",
  speaker: "Spoke",
  mentioned: "Named in transcript",
};

function reasonFor(detail: SessionDetail, contact: Contact, matter?: Matter): Reason | null {
  if (contact.session_ids?.includes(detail.id) || contact.session_id === detail.id) return "linked";
  const name = contact.name.trim().toLowerCase();
  if (name.length >= 3) {
    if (detail.transcript.some((s) => (s.speaker ?? "").trim().toLowerCase() === name)) return "speaker";
  }
  if (matter?.session_ids?.includes(detail.id)) return "matter";
  if (name.length >= 3 && detail.transcript.some((s) => !s.redacted && s.text.toLowerCase().includes(name))) return "mentioned";
  return null;
}

export function ContactProfilePage({ contactId }: { contactId: string }) {
  const contactQ = useQuery({ queryKey: ["contact", contactId], queryFn: () => hakiApi.getContact(contactId), retry: false });
  const mattersQ = useQuery({ queryKey: ["matters"], queryFn: hakiApi.listMatters, retry: false });
  const sessionsQ = useQuery({
    queryKey: ["sessions", { includeDemo: true }],
    queryFn: () => hakiApi.listSessions({ includeDemo: true }),
    refetchInterval: 20_000,
    retry: false,
  });
  const details = useQueries({
    queries: (sessionsQ.data ?? []).map((s) => ({
      queryKey: ["session", s.id],
      queryFn: () => hakiApi.getSession(s.id),
      refetchInterval: 20_000,
      retry: false,
    })),
  });
  const [editing, setEditing] = useState(false);

  const contact = contactQ.data;
  const matters = mattersQ.data ?? [];
  const matter = contact?.matter_id ? matters.find((m) => m.id === contact.matter_id) : undefined;

  const appearances: { detail: SessionDetail; reason: Reason }[] = [];
  const documents: TrackedDocument[] = [];
  const events: TrackedEvent[] = [];
  if (contact) {
    const lowerName = contact.name.trim().toLowerCase();
    for (const q of details) {
      const detail = q.data;
      if (!detail) continue;
      const reason = reasonFor(detail, contact, matter);
      for (const result of detail.action_results ?? []) {
        const ev = eventOf(result, detail);
        if (ev && (reason || ev.attendees.some((a) => a.toLowerCase().includes(lowerName)))) events.push(ev);
        if (!reason) continue;
        const doc = documentOf(result, detail);
        if (doc) documents.push(doc);
      }
      if (reason) appearances.push({ detail, reason });
    }
    appearances.sort((a, b) => new Date(b.detail.created_at).getTime() - new Date(a.detail.created_at).getTime());
    events.sort((a, b) => new Date(a.start ?? 0).getTime() - new Date(b.start ?? 0).getTime());
  }
  const loadingDetails = sessionsQ.isLoading || details.some((q) => q.isLoading);

  return (
    <PageShell back>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
        <Link to="/contacts" className="text-xs font-medium text-primary underline-offset-4 hover:underline">
          ← All contacts
        </Link>
        {contactQ.isError ? (
          <p className="mt-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {friendlyErrorMessage(contactQ.error, "This contact could not be found.")}
          </p>
        ) : !contact ? (
          <p className="mt-6 text-sm text-muted-foreground">Loading contact…</p>
        ) : (
          <>
            <header className="mt-4 border-b border-border pb-7">
              <div className="flex flex-wrap items-start gap-4">
                <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                  <UserRound className="size-6" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Contact profile</p>
                  <h1 className="mt-1 break-words font-serif text-3xl font-semibold leading-tight">{contact.name}</h1>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {field(contact, "role", "title") ? <Badge variant="secondary" className="capitalize">{field(contact, "role", "title")}</Badge> : null}
                    {field(contact, "organisation", "organization", "company") ? <Badge variant="outline">{field(contact, "organisation", "organization", "company")}</Badge> : null}
                    {field(contact, "source") ? <Badge variant="outline" className="text-muted-foreground">From {field(contact, "source")!.replace(/[_-]/g, " ")}</Badge> : null}
                  </div>
                </div>
                <Button variant="outline" onClick={() => setEditing(true)}>
                  <Pencil className="size-4" />Edit details
                </Button>
              </div>
              <ContactDetails contact={contact} matter={matter} />
            </header>

            <section className="mt-8">
              <SectionHeading eyebrow="Sessions" title={`Appears in ${appearances.length} session${appearances.length === 1 ? "" : "s"}`} />
              {appearances.length === 0 ? (
                <Empty text={loadingDetails ? "Looking through your sessions…" : "Not linked to any session yet. Link one from Edit details, or name this person as a speaker."} />
              ) : (
                <ul className="mt-4 grid gap-2">
                  {appearances.map(({ detail, reason }) => (
                    <li key={detail.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card p-3">
                      <SourceIcon source={detail.source} />
                      <div className="min-w-0 flex-1">
                        <Link to="/sessions/$sessionId" params={{ sessionId: detail.id }} search={{ fresh: false }} className="block truncate font-medium text-primary underline-offset-4 hover:underline">
                          {detail.title}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {formatDay(detail.created_at)} · {detail.flagged_moments.length} flags · {detail.transcript.length} lines
                        </p>
                      </div>
                      <Badge variant={reason === "linked" || reason === "speaker" ? "secondary" : "outline"}>{REASON_LABEL[reason]}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="mt-8">
              <SectionHeading eyebrow="Documents" title={`${documents.length} drafted document${documents.length === 1 ? "" : "s"}`} />
              {documents.length === 0 ? (
                <Empty text="No drafted documents from these sessions yet." />
              ) : (
                <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                  {documents.map((d, i) => (
                    <li key={`${d.sessionId}-${i}`} className="rounded-lg border border-border bg-card p-3">
                      <p className="flex items-center gap-2 font-medium capitalize"><FileText className="size-4 text-primary" />{d.kind}</p>
                      <p className="mt-1 truncate text-xs text-muted-foreground">{d.sessionTitle} · {formatDate(d.createdAt)}</p>
                      {d.url ? (
                        <a href={d.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary underline-offset-4 hover:underline">
                          Open document <ExternalLink className="size-3" />
                        </a>
                      ) : (
                        <p className="mt-2 text-xs text-muted-foreground">On the record only</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="mt-8">
              <SectionHeading eyebrow="Diary" title={`${events.length} diary entr${events.length === 1 ? "y" : "ies"}`} />
              {events.length === 0 ? (
                <Empty text="No appointments or court dates involving this person yet." />
              ) : (
                <ul className="mt-4 grid gap-2">
                  {events.map((e, i) => (
                    <li key={`${e.sessionId}-${i}`} className="rounded-lg border border-border bg-card p-3">
                      <p className="flex items-center gap-2 font-medium"><CalendarClock className="size-4 text-primary" />{e.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatDate(e.start)}{e.location ? ` · ${e.location}` : ""} · from {e.sessionTitle}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <EditContactDialog open={editing} onOpenChange={setEditing} contact={contact} matters={matters} sessions={(sessionsQ.data ?? []).map((s) => ({ id: s.id, title: s.title }))} />
          </>
        )}
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="mt-4 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">{text}</p>;
}

function ContactDetails({ contact, matter }: { contact: Contact; matter?: Matter | undefined }) {
  const email = field(contact, "email");
  const phone = field(contact, "phone", "phone_number");
  const address = field(contact, "address");
  const notes = field(contact, "notes");
  const extras = Object.entries(contact.updates ?? {}).filter(
    ([k, v]) => !HIDDEN.has(k) && (typeof v === "string" || typeof v === "number") && String(v).trim(),
  );
  return (
    <div className="mt-5 grid gap-4 sm:grid-cols-2">
      <div className="grid gap-2 text-sm">
        {email ? <a href={`mailto:${email}`} className="flex items-center gap-2 text-primary hover:underline"><Mail className="size-4" />{email}</a> : null}
        {phone ? <a href={`tel:${phone}`} className="flex items-center gap-2 text-primary hover:underline"><Phone className="size-4" />{phone}</a> : null}
        {address ? <p className="flex items-center gap-2"><MapPin className="size-4 text-muted-foreground" />{address}</p> : null}
        {!email && !phone && !address ? <p className="text-muted-foreground">No email, phone or address yet — use Edit details to add them.</p> : null}
        <p className="flex items-center gap-2"><Scale className="size-4 text-muted-foreground" />{matter ? matter.matter_name : <span className="text-muted-foreground">No matter linked</span>}</p>
      </div>
      <div className="grid content-start gap-1 text-sm">
        {extras.map(([k, v]) => (
          <p key={k}><span className="capitalize text-muted-foreground">{k.replace(/[_-]/g, " ")}:</span> {String(v)}</p>
        ))}
        {notes ? <p className="whitespace-pre-wrap rounded-md border border-border bg-muted/30 p-3 text-sm">{notes}</p> : null}
      </div>
    </div>
  );
}

function EditContactDialog({
  open,
  onOpenChange,
  contact,
  matters,
  sessions,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  contact: Contact;
  matters: Matter[];
  sessions: { id: string; title: string }[];
}) {
  const qc = useQueryClient();
  const initCore = () => Object.fromEntries(CORE_FIELDS.map((f) => [f.key, field(contact, f.key, ...(f.aliases ?? [])) ?? ""]));
  const initExtras = () =>
    Object.entries(contact.updates ?? {})
      .filter(([k, v]) => !HIDDEN.has(k) && (typeof v === "string" || typeof v === "number"))
      .map(([k, v]) => ({ key: k, value: String(v) }));
  const [name, setName] = useState(contact.name);
  const [core, setCore] = useState<Record<string, string>>(initCore);
  const [notes, setNotes] = useState(field(contact, "notes") ?? "");
  const [extras, setExtras] = useState(initExtras);
  const [matterId, setMatterId] = useState(contact.matter_id ?? NONE);
  const [linked, setLinked] = useState<string[]>(contact.session_ids ?? (contact.session_id ? [contact.session_id] : []));
  const [addSession, setAddSession] = useState(NONE);

  const reset = (v: boolean) => {
    if (v) {
      setName(contact.name); setCore(initCore()); setNotes(field(contact, "notes") ?? "");
      setExtras(initExtras()); setMatterId(contact.matter_id ?? NONE);
      setLinked(contact.session_ids ?? (contact.session_id ? [contact.session_id] : []));
    }
    onOpenChange(v);
  };

  const save = useMutation({
    mutationFn: () => {
      // Keep untouched non-string details (and source); drop old aliases replaced by the core keys.
      const aliases = new Set(CORE_FIELDS.flatMap((f) => f.aliases ?? []));
      const kept = Object.fromEntries(
        Object.entries(contact.updates ?? {}).filter(([k, v]) => k === "source" || (!HIDDEN.has(k) && !aliases.has(k) && typeof v !== "string" && typeof v !== "number")),
      );
      const updates: Record<string, unknown> = { ...kept };
      for (const f of CORE_FIELDS) if (core[f.key]?.trim()) updates[f.key] = core[f.key]!.trim();
      if (notes.trim()) updates["notes"] = notes.trim();
      for (const { key, value } of extras) {
        const k = key.trim().toLowerCase().replace(/\s+/g, "_");
        if (k && value.trim() && !HIDDEN.has(k)) updates[k] = value.trim();
      }
      return hakiApi.updateContact(contact.id, {
        name: name.trim(),
        updates,
        ...(matterId === NONE ? { clear_matter: true } : { matter_id: matterId }),
        session_ids: linked,
      });
    },
    onSuccess: (updated) => {
      toast.success(`${updated.name} saved`);
      qc.setQueryData(["contact", contact.id], updated);
      void qc.invalidateQueries({ queryKey: ["contacts"] });
      void qc.invalidateQueries({ queryKey: ["matters"] });
      onOpenChange(false);
    },
    onError: (e) => toast.error(friendlyErrorMessage(e, "The contact could not be saved.")),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (name.trim()) save.mutate();
  };
  const titleOf = (id: string) => sessions.find((s) => s.id === id)?.title ?? "Session";

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit contact</DialogTitle>
          <DialogDescription>Update how to reach this person and where they appear. Leave a field empty to remove it.</DialogDescription>
        </DialogHeader>
        <form id="edit-contact" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <div className="grid gap-1.5 sm:col-span-2"><Label htmlFor="ec-name">Name</Label><Input id="ec-name" value={name} onChange={(e) => setName(e.target.value)} required /></div>
          {CORE_FIELDS.map((f) => (
            <div key={f.key} className={f.key === "address" ? "grid gap-1.5 sm:col-span-2" : "grid gap-1.5"}>
              <Label htmlFor={`ec-${f.key}`}>{f.label}</Label>
              <Input id={`ec-${f.key}`} type={f.type ?? "text"} value={core[f.key] ?? ""} onChange={(e) => setCore({ ...core, [f.key]: e.target.value })} />
            </div>
          ))}
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
          <div className="grid gap-2 sm:col-span-2">
            <Label>Linked sessions</Label>
            {linked.length ? (
              <div className="flex flex-wrap gap-1.5">
                {linked.map((id) => (
                  <Badge key={id} variant="secondary" className="gap-1">
                    {titleOf(id)}
                    <button type="button" aria-label={`Unlink ${titleOf(id)}`} onClick={() => setLinked(linked.filter((x) => x !== id))} className="ml-1 text-muted-foreground hover:text-foreground">×</button>
                  </Badge>
                ))}
              </div>
            ) : <p className="text-xs text-muted-foreground">Not linked to a session.</p>}
            <Select value={addSession} onValueChange={(v) => { if (v !== NONE && !linked.includes(v)) setLinked([...linked, v]); setAddSession(NONE); }}>
              <SelectTrigger aria-label="Link a session"><SelectValue placeholder="Link a session" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>Link a session…</SelectItem>
                {sessions.filter((s) => !linked.includes(s.id)).map((s) => <SelectItem key={s.id} value={s.id}>{s.title}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2 sm:col-span-2">
            <Label>Other details</Label>
            {extras.map((row, i) => (
              <div key={i} className="flex gap-2">
                <Input aria-label="Detail name" placeholder="e.g. ID number" value={row.key} onChange={(e) => setExtras(extras.map((r, j) => (j === i ? { ...r, key: e.target.value } : r)))} className="w-2/5" />
                <Input aria-label="Detail value" value={row.value} onChange={(e) => setExtras(extras.map((r, j) => (j === i ? { ...r, value: e.target.value } : r)))} />
                <Button type="button" variant="ghost" size="icon" aria-label="Remove detail" onClick={() => setExtras(extras.filter((_, j) => j !== i))}><Trash2 className="size-4" /></Button>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" className="justify-self-start" onClick={() => setExtras([...extras, { key: "", value: "" }])}>
              <Plus className="size-4" />Add detail
            </Button>
          </div>
          <div className="grid gap-1.5 sm:col-span-2"><Label htmlFor="ec-notes">Notes</Label><Textarea id="ec-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
        </form>
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button type="submit" form="edit-contact" disabled={!name.trim() || save.isPending}>{save.isPending ? "Saving…" : "Save changes"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
