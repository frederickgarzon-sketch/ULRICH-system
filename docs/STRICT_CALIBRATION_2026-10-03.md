# Actual-test calibration: bypass removal

Temporary missing-joint and session-start overrides were removed from both UI and backend. Legacy session requests containing `verification_override` are rejected. The framing-override endpoint no longer exists. Required body framing and live checks must pass normally.

The calibration configuration schema is now `calibration-1.1-strict`, invalidating prior room-setup fingerprints. Complete and accept a new room setup once. Daily operation is then **Select participant → Start session**; Start session silently samples live face/body readiness for two seconds and saves that automatic result. Historical records remain unchanged; this update does not retroactively validate previous overridden sessions.

Local `.env` remains in real mode. No server was started and no ZIP was rebuilt by this change. Restart/open the updated application before testing.
