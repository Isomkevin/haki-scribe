import { Link } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ArrowLeft, BookOpen, ExternalLink, Scale, ShieldCheck, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Brand, TrustLine } from "./brand";
import { hakiApi, hasApiConfiguration, friendlyErrorMessage } from "@/lib/hakiscribe";
import { researchTranscript, type ResearchReport } from "@/lib/research.functions";

function transcriptText(segments: { speaker: string | null; text: string; redacted: boolean }[]) {
  return segments
    .filter((segment) => !segment.redacted)
    .map((segment) => `${segment.speaker ?? "Speaker"}: ${segment.text}`)
    .join("\n");
}

export function ResearchPage({ sessionId }: { sessionId?: string }) {
  const [selectedId, setSelectedId] = useState(sessionId ?? "");
  const [question, setQuestion] = useState("");

  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: hakiApi.listSessions,
    enabled: hasApiConfiguration,
  });
  const activeId = selectedId || sessions.data?.[0]?.id || "";
  const session = useQuery({
    queryKey: ["session", activeId],
    queryFn: () => hakiApi.getSession(activeId),
    enabled: Boolean(activeId) && hasApiConfiguration,
  });

  const record = useMemo(() => (session.data ? transcriptText(session.data.transcript) : ""), [session.data]);
  const run = useServerFn(researchTranscript);
  const research = useMutation<ResearchReport, Error>({
    mutationFn: () =>
      run({
        data: {
          question:
            question.trim() ||
            "Identify every point of Kenyan law raised on this record and the authorities that govern it.",
          transcript: record,
          matter: session.data?.matters?.[0]?.matter_name ?? session.data?.title ?? "",
        },
      }),
  });
  const report = research.data;

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10 lg:py-12">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
        <Brand compact />
        <Button asChild variant="ghost" size="sm">
          <Link to="/"><ArrowLeft /> Sessions</Link>
        </Button>
      </div>

      <header className="mt-7 border-b border-border pb-7 sm:mt-8 sm:pb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Legal research</p>
        <h1 className="mt-2 max-w-3xl font-serif text-3xl font-semibold leading-tight sm:text-4xl">
          Kenyan case law, statutes and precedent for this conversation
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
          Research is grounded in the verified, non-redacted transcript. Every authority is cited so you can open and
          confirm it before it reaches a pleading.
        </p>
        <TrustLine className="mt-5 max-w-full rounded-md border border-border bg-card px-3 py-2 text-left sm:rounded-full sm:py-1.5" />
      </header>

      {!hasApiConfiguration ? (
        <p className="mt-8 text-sm text-destructive">HakiScribe cannot reach its session service right now.</p>
      ) : (
        <section className="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
          <div className="min-w-0 space-y-4">
          <div>
            <label htmlFor="research-session" className="text-sm font-medium">Session on the record</label>
            <select
              id="research-session"
              value={activeId}
              onChange={(event) => { setSelectedId(event.target.value); research.reset(); }}
              className="mt-2 h-11 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              {(sessions.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.title}</option>
              ))}
            </select>
            <p className="mt-2 text-xs text-muted-foreground">
              {session.data
                ? `${session.data.transcript.filter((segment) => !segment.redacted).length} verified lines will be read. Locked lines are excluded.`
                : "Loading the record…"}
            </p>
          </div>

          <div>
            <label htmlFor="research-question" className="text-sm font-medium">Research question (optional)</label>
            <Textarea
              id="research-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="e.g. Was the termination procedurally fair under section 41 of the Employment Act?"
              className="mt-2 min-h-24"
            />
          </div>

          <Button
            variant="warm"
            size="lg"
            className="h-12 w-full"
            disabled={!record || research.isPending}
            onClick={() => research.mutate()}
          >
            <Scale /> {research.isPending ? "Researching Kenyan authorities…" : "Run legal research"}
          </Button>
          {research.isPending && (
            <p className="text-center text-xs text-muted-foreground">
              Reading the record and checking authorities. This takes a minute or two.
            </p>
          )}
          {research.error && (
            <p className="text-sm text-destructive">
              {friendlyErrorMessage(research.error, "Legal research could not finish. Try again in a moment.")}
            </p>
          )}
          </div>
          <aside className="rounded-lg border border-border bg-muted/40 p-4 text-xs leading-5 text-muted-foreground lg:sticky lg:top-6">
            <p className="font-semibold text-foreground">Research safeguards</p>
            <p className="mt-2">Locked lines stay excluded. Open every cited authority before relying on it in filed work.</p>
          </aside>
        </section>
      )}

      {report && <ResearchReportView report={report} />}
    </main>
  );
}

export function ResearchReportView({ report }: { report: ResearchReport }) {
  return (
    <section className="mt-9 space-y-4 sm:mt-10 sm:space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={report.grounding === "live_sources" ? "default" : "outline"}>
          {report.grounding === "live_sources" ? <ShieldCheck /> : <TriangleAlert />}
          {report.grounding === "live_sources" ? "Answered from retrieved sources" : "From model knowledge — verify"}
        </Badge>
        <Badge variant="outline">{report.model}</Badge>
      </div>

      {report.summary && (
        <div className="chamber-card rounded-lg border border-border bg-card p-4 sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Position</p>
          <p className="mt-2 whitespace-pre-wrap font-serif text-base leading-7">{report.summary}</p>
        </div>
      )}

      {report.issues.map((issue, index) => (
        <article key={`${issue.issue}-${index}`} className="chamber-card rounded-lg border border-border bg-card p-4 sm:p-6">
          <h2 className="font-serif text-xl font-semibold">{issue.issue}</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-7">{issue.analysis}</p>
          <ul className="mt-4 space-y-3 border-t border-border pt-4">
            {issue.authorities.map((authority, position) => (
              <li key={`${authority.citation}-${position}`} className="text-sm">
                <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-2 gap-y-1 sm:flex sm:flex-wrap sm:items-center">
                  <BookOpen className="mt-0.5 size-4 shrink-0 text-muted-foreground sm:mt-0" />
                  <span className="min-w-0 break-words font-medium">{authority.citation}</span>
                  <Badge variant="outline" className="text-[0.65rem] uppercase">{authority.kind}</Badge>
                  {authority.verified ? (
                    <Badge variant="secondary" className="text-[0.65rem]">Source retrieved</Badge>
                  ) : (
                    <Badge variant="outline" className="text-[0.65rem] text-muted-foreground">Verify before use</Badge>
                  )}
                </div>
                <p className="mt-1 leading-6 text-muted-foreground sm:pl-6">{authority.relevance}</p>
                {authority.url && (
                  <a
                    href={authority.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex min-h-8 items-center gap-1 text-xs text-primary underline sm:ml-6"
                  >
                    Open authority <ExternalLink className="size-3" />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </article>
      ))}

      {report.sources.length > 0 && (
        <div className="rounded-lg border border-border bg-muted/40 p-4 sm:p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Sources read</p>
          <ul className="mt-3 space-y-2 text-sm">
            {report.sources.map((source) => (
              <li key={source.url}>
                <a href={source.url} target="_blank" rel="noreferrer" className="break-words text-primary underline">{source.title}</a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.caveats.length > 0 && (
        <div className="rounded-lg border border-dashed border-border p-4 sm:p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Before you rely on this</p>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted-foreground">
            {report.caveats.map((caveat, index) => <li key={index}>{caveat}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}
