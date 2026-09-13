# Mobile-first platform refinement

## Goal
Make every HakiScribe screen comfortable to use on a phone first, while using tablet and desktop space for faster legal review rather than simply stretching the mobile layout.

## Changes
- Tighten the home screen on phones: put session creation first, reduce introductory content density, and keep library rows readable without clipped status or metadata.
- Make shared headers, section headings, progress steps, footers, trust labels, and error states resilient at narrow widths with touch-friendly controls.
- Refine recording and verification screens for short phone viewports: stable controls, compact waveform/captions, full-width primary actions, and safe sticky bottom spacing.
- Rework the Action Tray navigation and controls into mobile-safe grids; keep selection and generation reachable without covering content.
- Make action, research, news, source, and generated-result cards scan cleanly on phones while using multi-column layouts on larger screens.
- Improve long document editing and result actions on mobile, while widening review areas and side-by-side information on desktop where useful.
- Preserve the existing HakiChain visual system, real API behavior, and all current workflows.

## Technical details
- Use mobile-first Tailwind utilities, `minmax(0,1fr)` grids, `min-w-0`, `shrink-0`, safe-area padding, and stable touch target heights.
- Avoid horizontal page overflow; allow intentional horizontal scrolling only for compact tab or chip rows.
- Keep phone typography and spacing compact without viewport-scaled font sizes.
- Add a small set of reusable responsive layout utilities only where existing classes cannot express the behavior cleanly.

## Validation
- Check `/`, a session workspace, and `/research` at phone, tablet, laptop, and wide desktop sizes.
- Verify no clipped text, overlapping controls, hidden sticky actions, or accidental horizontal scrolling.
- Confirm recording, verification, Action Tray, research/news, and generated results remain fully usable by touch and keyboard.
