<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

- Use the supplied HakiScribe microphone-and-gavel logo assets for brand identity; keep functional legal-context icons separate. This preserves the approved brand while retaining clear interface meaning.
- Dual deployment (Lovable + Vercel) comes from nitro's preset detection — Lovable builds `cloudflare-module`, Vercel builds the Build Output API from the same source. Never add platform-specific build config (e.g. `vercel.json`) unless a verified failure requires it, and keep `bun.lock` and `package-lock.json` in sync so either package manager can install on either platform.
