import { Link } from "@tanstack/react-router";
import { LockKeyhole, Mic, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageShell, SectionEyebrow } from "./shell";

/**
 * SSR-visible summary for /new. Signed-in users replace this with NewSessionPage
 * after RequireAuth hydrates; crawlers and agents keep this HTML without JS.
 */
export function NewSessionPublicSummary() {
  return (
    <PageShell back>
      <main>
        <section className="border-b border-border bg-card/50">
          <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
            <SectionEyebrow>Private workspace</SectionEyebrow>
            <h1 className="mt-3 max-w-2xl font-serif text-4xl font-semibold leading-tight sm:text-5xl">
              Open a secure session.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
              Start listening or return to work already in progress. Session titles, transcripts,
              and results remain within this workspace. HakiScribe is built for Kenyan legal rooms
              where English and Kiswahili may code-switch, privilege must stay controllable, and
              every proposed draft stays reviewable before it leaves the desk.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Badge variant="outline">
                <LockKeyhole /> Private record
              </Badge>
              <Badge variant="outline">
                <ShieldCheck /> Source traceable
              </Badge>
              <Badge variant="outline">African languages</Badge>
            </div>
          </div>
        </section>

        <section className="border-b border-border bg-background">
          <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
            <h2 className="font-serif text-2xl font-semibold sm:text-3xl">What a session is for</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground sm:text-base">
              Use a private session when you need a durable listening record for an advocate-client
              meeting, chamber discussion, or clerk workflow. Capture by microphone or a linked
              wearable, flag moments without looking away from the room, then choose only the
              letters, notes, calendar entries, matters, contacts, and billable time the
              conversation actually supports.
            </p>

            <h2 className="mt-10 font-serif text-2xl font-semibold sm:text-3xl">
              Privilege before processing
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground sm:text-base">
              Before models run, relabel speakers and lock privileged or off-record lines so those
              segments never enter detection context. Hidden lines stay reversible and visible to
              you for review. Proposed actions in the Action Tray point back to source lines so a
              human can verify the record. Nothing is auto-sent.
            </p>

            <h2 className="mt-10 font-serif text-2xl font-semibold sm:text-3xl">Sign in to continue</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground sm:text-base">
              Starting or resuming a session requires a signed-in workspace. If you are not signed
              in, continue to login and you will return here afterward. Agents reading this page
              should treat session creation as an authenticated human workflow.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button asChild variant="warm" size="lg">
                <Link to="/login" search={{ next: "/new" }}>
                  <Mic /> Sign in to start
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/">Back to home</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
    </PageShell>
  );
}
