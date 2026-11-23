# HakiChain ↔ HakiScribe Phase 1 acceptance checklist

Contract: `2026-11`. Identity: dual login + `hkc_` bridge (1B).

## Automated (this repo)

- [ ] `python -m unittest tests.test_hearing_filing tests.test_hakichain_pull tests.test_hakichain_client -v`
- [ ] Frontend typecheck / vitest if Tracker changes touch shared types

## Automated (hakichain-demo-suite)

- [ ] Apply migration `20261123100000_hakiscribe_hearings.sql`
- [ ] Deploy / serve updated `hakiscribe-ingress`
- [ ] Unit: `src/lib/hakiscribeIngress.test.ts` (existing helpers still pass)
- [ ] Manual: Workspace → Hearings tab loads without error when tables exist

## Live E2E (requires real `hkc_` + deployed ingress)

1. [ ] Lawyer authenticates in HakiChain; mints `hkc_` under Account Settings → HakiScribe
2. [ ] HakiScribe Settings → Connectors → HakiChain: paste token; `me` succeeds
3. [ ] Tracker → Load HakiChain matters → only accessible matters appear
4. [ ] Link local matter → selected WorkSpace; matter shows `(linked)` / “HakiChain linked”
5. [ ] Hearing confirm → process (optional `local_only`) → Mark reviewed → File to HakiChain
6. [ ] HakiChain Workspace → Hearings: transcript segments + proceedings visible; activity notes filing
7. [ ] Next-date reminder present; court-date appears on schedule snapshot when applicable
8. [ ] No duplicate `hs-{uuid}` workspace invented when linking an existing matter

## Failure cases

- [ ] No token / revoked token → clear 400/401, hearing stays `reviewed`
- [ ] Inaccessible `workspace_id` → 403 from ingress; link fails without writing FKs
- [ ] Re-file same hearing → finalize upserts content (not frozen blank reuse)
- [ ] Partial network failure mid-file → retry File to HakiChain succeeds idempotently

## Out of scope for this checklist

SSO replacement, live Zoom/Teams tenant proof, HakiDraft/Lens/Review deep workflows, firm-wide tokens.
