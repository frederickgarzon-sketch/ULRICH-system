# Startup import failure — 2026-11-19

Client traceback: ModuleNotFoundError: No module named 'app.sessions'.

Root cause confirmed locally: the repository .gitignore used an unanchored
sessions/ rule, excluding the source package app/sessions. The source existed
locally but was not tracked, so GitHub downloads omitted it. This was not a
camera configuration error; import failed before application startup.

Local repair: anchor the runtime exclusion as /sessions/, include the source
package and session_manager.py, and remove the launcher's misleading camera
conflict conclusion. Add a dependency-free tracked-source import inventory
script and regression tests. All app/analysis/rpi_node absolute import targets
are checked against Git's index, rather than merely local disk contents.

Verification: source inventory passed; 13 focused Python tests passed (two source
inventory checks plus eleven shape persistence/export checks). Full application
startup with AI dependencies and physical cameras has not been verified here.
No database deletion, .env modification, camera reconfiguration or release ZIP.

Delivery requires the corrected source files to be committed/pushed, then the
client must update their existing source folder without overwriting .env or data.
The access key pasted in the support log should be rotated locally before real
use; no key value is stored in this document and no credential was changed.
