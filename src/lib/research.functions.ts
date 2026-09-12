import { createServerFn } from "@tanstack/react-start";

export interface ResearchAuthority {
  citation: string;
  kind: string;
  relevance: string;
  url: string | null;
  verified: boolean;
}

export interface ResearchIssue {
  issue: string;
  analysis: string;
  authorities: ResearchAuthority[];
}

export interface ResearchSourceLink {
  title: string;
  url: string;
  extract: string;
}

export interface ResearchReport {
  matter: string;
  question: string;
  summary: string;
  issues: ResearchIssue[];
  caveats: string[];
  sources: ResearchSourceLink[];
  grounding: "live_sources" | "model_knowledge";
  model: string;
}

const GATEWAY = "https://ai.gateway.lovable.dev/v1/responses";
const MODEL = "openai/gpt-6-astra";

const LEGAL_DOMAINS = [
  "kenyalaw.org",
  "new.kenyalaw.org",
  "klrc.go.ke",
  "judiciary.go.ke",
  "parliament.go.ke",
];

const REPORT_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["summary", "issues", "caveats"],
  properties: {
    summary: { type: "string" },
    caveats: { type: "array", items: { type: "string" } },
    issues: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["issue", "analysis", "authorities"],
        properties: {
          issue: { type: "string" },
          analysis: { type: "string" },
          authorities: {
            type: "array",
            items: {
              type: "object",
              additionalProperties: false,
              required: ["citation", "kind", "relevance", "url"],
              properties: {
                citation: { type: "string" },
                kind: { type: "string" },
                relevance: { type: "string" },
                url: { type: ["string", "null"] },
              },
            },
          },
        },
      },
    },
  },
} as const;

async function searchLegalSources(query: string): Promise<ResearchSourceLink[]> {
  const key = process.env["EXA_API_KEY"];
  if (!key) return [];
  try {
    const response = await fetch("https://api.exa.ai/search", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": key },
      body: JSON.stringify({
        query: `${query} Kenya law`,
        numResults: 6,
        type: "auto",
        includeDomains: LEGAL_DOMAINS,
        contents: { text: { maxCharacters: 1200 } },
      }),
    });
    if (!response.ok) {
      console.error(`Exa search failed [${response.status}]: ${await response.text()}`);
      return [];
    }
    const payload = (await response.json()) as { results?: { title?: string; url?: string; text?: string }[] };
    return (payload.results ?? [])
      .filter((item): item is { title?: string; url: string; text?: string } => Boolean(item.url))
      .map((item) => ({
        title: item.title?.trim() || item.url,
        url: item.url,
        extract: (item.text ?? "").slice(0, 900).trim(),
      }));
  } catch (error) {
    console.error("Exa search error", error);
    return [];
  }
}

function buildPrompt(args: {
  question: string;
  transcript: string;
  matter: string;
  sources: ResearchSourceLink[];
}) {
  const sourceBlock = args.sources.length
    ? args.sources
        .map((source, index) => `[${index + 1}] ${source.title} — ${source.url}\n${source.extract}`)
        .join("\n\n")
    : "NONE RETRIEVED";
  return [
    `MATTER: ${args.matter || "unnamed matter"}`,
    `RESEARCH QUESTION: ${args.question}`,
    "",
    "VERIFIED TRANSCRIPT (the only facts you may treat as true):",
    args.transcript || "(no transcript supplied)",
    "",
    "RETRIEVED KENYAN LEGAL SOURCES:",
    sourceBlock,
    "",
    "Produce the research report as json following the schema.",
  ].join("\n");
}

const SYSTEM = [
  "You are a Kenyan legal research assistant working for advocates who are professionally liable for what they file.",
  "Identify the legal issues actually raised by the transcript and answer them under Kenyan law: the Constitution of Kenya 2010, Acts of Parliament, subsidiary legislation, the Civil Procedure Rules, and reported Kenyan case law.",
  "Cite each authority precisely: statute name, year and section; or case name, citation and court.",
  "When retrieved sources are supplied, prefer them and reuse their exact URLs.",
  "Never invent a case name, citation, section number, party or figure. If you are drawing on recall rather than a supplied source, still give the citation but keep url null so it is flagged for verification.",
  "Never state a fact about the matter that is not in the transcript; bracket anything unknown, e.g. [NOT ON THE RECORD].",
  "Write for a Kenyan advocate: precise, unpadded, no disclaimers beyond the caveats field.",
].join(" ");

export const researchTranscript = createServerFn({ method: "POST" })
  .inputValidator((input: { question: string; transcript: string; matter?: string }) => {
    const question = (input.question ?? "").trim();
    if (!question) throw new Error("A research question is required.");
    return {
      question: question.slice(0, 1000),
      transcript: (input.transcript ?? "").slice(0, 24000),
      matter: (input.matter ?? "").slice(0, 300),
    };
  })
  .handler(async ({ data }): Promise<ResearchReport> => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) throw new Error("Legal research is not configured on this workspace.");

    const sources = await searchLegalSources(data.question);

    const response = await fetch(GATEWAY, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Lovable-API-Key": apiKey,
        "X-Lovable-AIG-SDK": "fetch",
      },
      body: JSON.stringify({
        model: MODEL,
        stream: true,
        instructions: SYSTEM,
        input: buildPrompt({ ...data, sources }),
        reasoning: { effort: "medium", summary: "auto" },
        text: {
          format: {
            type: "json_schema",
            name: "kenyan_legal_research",
            strict: true,
            schema: REPORT_SCHEMA,
          },
        },
      }),
    });

    if (!response.ok || !response.body) {
      const body = await response.text();
      console.error(`Legal research request failed [${response.status}]: ${body}`);
      if (response.status === 402) throw new Error("This workspace is out of AI credits, so research could not run.");
      if (response.status === 429) throw new Error("Research is rate limited right now — try again shortly.");
      throw new Error(`Research could not be completed (${response.status}).`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let text = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === "[DONE]") continue;
        try {
          const event = JSON.parse(payload) as { type?: string; delta?: string };
          if (event.type === "response.output_text.delta" && typeof event.delta === "string") {
            text += event.delta;
          }
        } catch {
          // Ignore keep-alive and non-JSON frames.
        }
      }
    }

    let parsed: { summary?: string; issues?: ResearchIssue[]; caveats?: string[] } = {};
    try {
      parsed = JSON.parse(text) as typeof parsed;
    } catch {
      throw new Error("The research service returned an unreadable answer. Try again.");
    }

    const grounding: ResearchReport["grounding"] = sources.length ? "live_sources" : "model_knowledge";
    const issues = (parsed.issues ?? []).map((issue) => ({
      issue: issue.issue,
      analysis: issue.analysis,
      authorities: (issue.authorities ?? []).map((authority) => ({
        citation: authority.citation,
        kind: authority.kind,
        relevance: authority.relevance,
        url: authority.url ?? null,
        verified: Boolean(authority.url && sources.some((source) => source.url === authority.url)),
      })),
    }));

    const caveats = parsed.caveats ?? [];
    if (grounding === "model_knowledge") {
      caveats.unshift(
        "No live Kenyan law sources were retrieved, so every authority below comes from the model's own knowledge and must be checked on Kenya Law before it is relied on or filed.",
      );
    }

    return {
      matter: data.matter,
      question: data.question,
      summary: parsed.summary ?? "",
      issues,
      caveats,
      sources,
      grounding,
      model: MODEL,
    };
  });
