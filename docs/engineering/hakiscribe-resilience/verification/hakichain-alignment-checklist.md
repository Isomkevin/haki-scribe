# HakiChain ↔ HakiScribe acceptance checklist (Phases 1–3)

Contract: `2026-11`. Identity: dual login + `hkc_` bridge (1B).

## Automated (this repo)

- [x] `python -m unittest tests.test_hearing_filing tests.test_hakichain_pull tests.test_hakichain_client tests.test_hakichain_sync -v` (12 tests OK)
- [ ] Frontend typecheck / vitest if Tracker changes touch shared types

## Automated (hakichain-demo-suite)

- [ ] Apply migrations `20261123100000_hakiscribe_hearings.sql` + `20261123120000_hakiscribe_phase2_webhooks_firm.sql`
- [ ] Deploy / serve updated `hakiscribe-ingress`
- [ ] Unit: `src/lib/hakiscribeIngress.test.ts` (existing helpers still pass)
- [ ] Manual: Workspace → Hearings tab loads; Client Portal shows published summaries only
- [ ] Manual: Account Settings → HakiScribe: personal + firm token mint; webhook register

## Live E2E (requires real `hkc_` + deployed ingress)

1. [ ] Lawyer authenticates in HakiChain; mints `hkc_` under Account Settings → HakiScribe
2. [ ] HakiScribe Settings → Connectors → HakiChain: paste token; `me` succeeds
3. [ ] Tracker → Load HakiChain matters → only accessible matters appear
4. [ ] Link local matter → selected WorkSpace; matter shows `(linked)` / “HakiChain linked”
5. [ ] Hearing confirm → process (optional `local_only`) → Mark reviewed → File to HakiChain
6. [ ] HakiChain Workspace → Hearings: transcript segments + proceedings visible; activity notes filing
7. [ ] Next-date reminder present; court-date appears on schedule snapshot when applicable
8. [ ] No duplicate `hs-{uuid}` workspace invented when linking an existing matter
9. [ ] Re-file updates document content (`updated: true`), does not freeze blank
10. [ ] Register webhook → hearing.filed delivery hits `/webhooks/hakichain` (signed)
11. [ ] Firm-scoped token lists colleagues’ owned matters; personal token does not
12. [ ] Publish client summary → Client Portal shows it; raw segments never appear
13. [ ] Deep links: Draft/Review/Lens/Docs honour `?hearing=` / `?ws=` / `?folder=hakiscribe-hearings`
14. [ ] Tracker `?hearing=` scrolls and highlights the row

## Failure cases

- [ ] No token / revoked token → clear 400/401, hearing stays `reviewed`
- [ ] Inaccessible `workspace_id` → 403 from ingress; link fails without writing FKs
- [ ] Re-file same hearing → finalize upserts content (not frozen blank reuse)
- [ ] Partial network failure mid-file → retry File to HakiChain succeeds idempotently
- [ ] Invalid webhook signature → 401 on Scribe receiver

## Out of scope

SSO replacement, live Zoom/Teams tenant proof, rewriting published Lovable git history.
