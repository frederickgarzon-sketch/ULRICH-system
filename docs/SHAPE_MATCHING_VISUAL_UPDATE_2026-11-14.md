# Shape Matching — uniform activity design

- Reuses Pop the Balloon's shared CSS tokens, header, participant sky/grass
  background, game HUD, progress card, instruction card, buttons and modal screens.
- Removed Shape Garden branding; Shape Matching remains the activity name.
- Added glossy colored shape pieces, a grounded pedestal and inset matching holes
  on cream-colored target cards. All matching targets share a neutral color so
  children must match shape, not merely color.
- Moved technical run/pairing controls and detailed rules into expandable groups.
- Preserved existing DOM IDs, game engine, recording API and save/retry behavior.
- CSS includes narrow-screen stacking, larger targets and reduced-motion support.
  Actual tablet/touch and 125–150% zoom acceptance remain pending.

Verification: 40 JavaScript tests passed, including three template/style-contract
tests and existing controller/balloon tests. 11 focused Python shape persistence
tests passed. Actual local browser preview loaded the shared stylesheet; tap a
circle to its matching home and pause controls were exercised. This is not a
full recorded-session or backend HTTP test. Desktop preview was visually checked;
the production server/cameras were not started.

Preview URL: http://127.0.0.1:8765/shape-matching (loopback-only, no saving).
No ZIP, commit or GitHub push. Balloon source/style files were not altered.
