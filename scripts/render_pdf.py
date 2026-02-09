"""Render Markdown reports to PDF using markdown + weasyprint."""

from pathlib import Path
import markdown
from weasyprint import HTML

ROOT = Path(__file__).parent.parent
REPORTS = ROOT / "reports"

CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       font-size: 11pt; line-height: 1.5; color: #1f2328; }
h1 { font-size: 22pt; border-bottom: 1px solid #d1d9e0; padding-bottom: 6px; }
h2 { font-size: 16pt; border-bottom: 1px solid #d1d9e0; padding-bottom: 4px; margin-top: 24px; }
h3 { font-size: 13pt; margin-top: 20px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }
th, td { border: 1px solid #d1d9e0; padding: 6px 10px; text-align: left; }
th { background: #f6f8fa; font-weight: 600; }
tr:nth-child(even) { background: #f6f8fa; }
blockquote { border-left: 3px solid #d1d9e0; margin: 12px 0; padding: 4px 16px; color: #636c76; }
code { background: #f6f8fa; padding: 2px 6px; border-radius: 4px; font-size: 10pt; }
pre { background: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
strong { font-weight: 600; }
a { color: #0969da; text-decoration: none; }
"""

MD_EXTENSIONS = ["tables", "fenced_code", "smarty"]

reports = [
    ("YOLO_vs_Gemini_Report.md", "YOLO_vs_Gemini_Report.pdf"),
    ("Claude_Skills_Report.md", "Claude_Skills_Report.pdf"),
]

for md_name, pdf_name in reports:
    md_path = REPORTS / md_name
    pdf_path = REPORTS / pdf_name
    print(f"Rendering {md_name} -> {pdf_name} ... ", end="", flush=True)

    md_text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=MD_EXTENSIONS)
    full_html = f"<html><head><style>{CSS}</style></head><body>{html_body}</body></html>"

    HTML(string=full_html).write_pdf(str(pdf_path))
    print(f"done ({pdf_path.stat().st_size / 1024:.0f} KB)")
