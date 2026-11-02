import { Link } from "@tanstack/react-router";
import { PageShell, SectionEyebrow, WorkspaceFooter } from "./shell";
import type { ABOUT_COPY } from "@/lib/trust-pages";

type TrustCopy = typeof ABOUT_COPY;

export function TrustPage({ copy }: { copy: TrustCopy }) {
  return (
    <PageShell>
      <main>
        <section className="border-b border-border bg-card/50">
          <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
            <SectionEyebrow>{copy.eyebrow}</SectionEyebrow>
            <h1 className="mt-3 max-w-3xl font-serif text-4xl font-semibold leading-tight sm:text-5xl">
              {copy.title}
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
              {copy.lead}
            </p>
          </div>
        </section>

        <section className="bg-background">
          <div className="mx-auto max-w-6xl space-y-12 px-4 py-12 sm:px-6 sm:py-16">
            {copy.sections.map((section) => (
              <article key={section.heading} className="max-w-3xl">
                <h2 className="font-serif text-2xl font-semibold sm:text-3xl">{section.heading}</h2>
                <p className="mt-3 text-sm leading-7 text-muted-foreground sm:text-base">
                  {section.body}
                </p>
              </article>
            ))}
            <p className="text-sm text-muted-foreground">
              <Link to="/" className="font-medium text-primary underline-offset-4 hover:underline">
                Back to home
              </Link>
            </p>
          </div>
        </section>
      </main>
      <WorkspaceFooter />
    </PageShell>
  );
}
