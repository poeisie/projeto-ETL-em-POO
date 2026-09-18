from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, ListFlowable

root = Path(__file__).resolve().parent.parent
source = root / "docs" / "documentacao_ajustes_etl.md"
out = root / "docs" / "documentacao_ajustes_etl.pdf"

styles = getSampleStyleSheet()
if "Bullet" not in styles:
    styles.add(ParagraphStyle(name="Bullet", parent=styles["BodyText"], leftIndent=18, firstLineIndent=-12, spaceAfter=6))
if "TitleCentered" not in styles:
    styles.add(ParagraphStyle(name="TitleCentered", parent=styles["Title"], alignment=1, spaceAfter=20))

content = []

with source.open("r", encoding="utf-8") as f:
    lines = f.read().splitlines()

for line in lines:
    if not line.strip():
        content.append(Spacer(1, 8))
        continue

    if line.startswith("# "):
        content.append(Paragraph(line[2:], styles["TitleCentered"]))
    elif line.startswith("## "):
        content.append(Paragraph(line[3:], styles["Heading2"]))
    elif line.startswith("### "):
        content.append(Paragraph(line[4:], styles["Heading3"]))
    elif line.startswith("- "):
        content.append(Paragraph(line[2:], styles["Bullet"]))
    elif line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. ") or line.startswith("4. ") or line.startswith("5. ") or line.startswith("6. "):
        content.append(Paragraph(line, styles["BodyText"]))
    else:
        content.append(Paragraph(line, styles["BodyText"]))

pdf = SimpleDocTemplate(str(out), pagesize=letter, title="Documentação ETL")
pdf.build(content)
print(f"PDF gerado em: {out}")
