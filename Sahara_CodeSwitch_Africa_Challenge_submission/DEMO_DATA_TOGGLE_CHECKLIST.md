# Demo Data toggle — manual test checklist

Preference: **Settings → Workspace → Use Demo Data** (stored in `localStorage` as `hakiscribe.workspace-settings.workspace.useDemoData`).

The login **Use demo credentials** CTA is intentionally **not** controlled by this toggle.

## Persistence

- [ ] Default is **ON** for a fresh browser profile.
- [ ] Flip to **OFF**, reload the app — toggle stays OFF; no flash of seeded demo rows before real state applies.
- [ ] Flip back to **ON**, reload — toggle stays ON; demo shortcuts return.

## When OFF

- [ ] Home: no “Open a completed judge demo” / multilingual demo buttons.
- [ ] Home: no auto “Restoring the desk” seed sync.
- [ ] Home: empty library shows “No sessions yet” without a “Load judge demo” button.
- [ ] Home / Settings recent / Case tracker: known seeded demo titles (Wanjiru, Otieno court seeds, Sahara seeds, etc.) do not appear.
- [ ] Stats (sessions / matters / ready) count only non-demo items.
- [ ] Refresh icon refetches live data; it does not call `/demo/sync`.

## When ON

- [ ] Auto library sync can restore seeds.
- [ ] Judge demo and multilingual demo shortcuts are available.
- [ ] Empty state can offer “Load judge demo”.

## Real data path (OFF)

- [ ] Start a mic (or Omi) session, finalize, and confirm it appears in the library and tracker.
- [ ] Empty library with zero real sessions is a clean empty state (not a broken layout).
- [ ] Toggle OFF → ON → OFF again: real sessions remain visible whenever OFF; demos only when ON.
