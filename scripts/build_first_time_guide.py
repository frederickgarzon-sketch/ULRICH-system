"""Build the client-facing first-time Windows setup guide."""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "Behavior_Monitor_First_Time_Windows_Setup.docx"

doc = Document()
section = doc.sections[0]
section.top_margin = Inches(0.78)
section.bottom_margin = Inches(0.7)
section.left_margin = Inches(0.9)
section.right_margin = Inches(0.9)

styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"].font.size = Pt(10.5)
styles["Normal"].paragraph_format.space_after = Pt(7)
for name, size in (("Title", 20), ("Heading 1", 12.5)):
    styles[name].font.name = "Aptos Display"
    styles[name].font.size = Pt(size)
    styles[name].font.color.rgb = RGBColor(0, 0, 0)
    ppr = styles[name]._element.pPr
    if ppr is not None:
        for border in ppr.findall(qn("w:pBdr")):
            ppr.remove(border)

title = doc.add_paragraph(style="Title")
title_run = title.add_run("Behavior Monitor First Time Windows Setup")
title_run.font.color.rgb = RGBColor(0, 0, 0)
doc.add_paragraph(
    "Use this guide when opening the research console on a new Windows computer. "
    "After one automatic setup, normal use is to double-click run_windows.bat. "
    "This is a copy-and-run package, not a standalone executable."
)

doc.add_heading("What the new computer needs", 1)
for item in (
    "Windows computer with 64-bit Python 3.11 installed.",
    "Internet access for the first package installation; later launches normally do not reinstall.",
    "Sufficient disk space, plus the camera and Raspberry Pi if those measurements are required.",
):
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("Start the system", 1)
for item in (
    "Extract the entire ZIP to a normal folder. Do not run it from inside the ZIP.",
    "Double-click run_windows.bat. On first launch, wait while it builds the local environment and database.",
    "Keep the server window open. The login page opens automatically. If not, visit http://127.0.0.1:8000/login on the same computer.",
    "Use the private owner access key displayed in the server window. Keep it confidential.",
):
    doc.add_paragraph(item, style="List Number")

doc.add_heading("If setup does not finish", 1)
for label, detail in (
    ("Python missing", "Install 64-bit Python 3.11 from python.org/downloads and select Add python.exe to PATH. Then run the BAT again."),
    ("Install failed", "Check internet access and free disk space, then retry. Ask the local administrator if downloads are blocked."),
    ("Port 8000 busy", "Close the other server window with Ctrl+C before starting this copy."),
    ("Origin error", "Make sure the old server is closed. Open exactly http://127.0.0.1:8000/login after starting this package."),
):
    p = doc.add_paragraph()
    p.add_run(label + ". ").bold = True
    p.add_run(detail)

doc.add_heading("Check the Raspberry Pi", 1)
doc.add_paragraph(
    "The default face and body camera URLs are http://adhd-camera.local:8090/stream/face "
    "and http://adhd-camera.local:8090/stream/body. "
    "On Windows PowerShell, run ping adhd-camera.local and then "
    "Test-NetConnection adhd-camera.local -Port 8090. If the name cannot be resolved, "
    "confirm both devices are on the same local network and enter the Pi LAN IP in "
    "FACE_CAMERA_SOURCE and BODY_CAMERA_SOURCE inside .env. Restart the BAT after changes."
)

doc.add_heading("Before sharing a copy", 1)
doc.add_paragraph(
    "Use the client-ready ZIP. It excludes .env, .venv and local databases. "
    "Do not share a working .env because it contains private login credentials. "
    "Participant data require a separate approved backup and transfer process."
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUTPUT)
print(OUTPUT)
