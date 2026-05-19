import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

md_path = os.path.join(os.path.dirname(__file__), 'PROJECT_OVERVIEW.md')
pdf_path = os.path.join(os.path.dirname(__file__), 'PROJECT_OVERVIEW.pdf')

if not os.path.exists(md_path):
    raise FileNotFoundError(f"Markdown source not found: {md_path}")

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

styles = getSampleStyleSheet()
# customize styles
styles.add(ParagraphStyle(name='Heading1', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=12))
styles.add(ParagraphStyle(name='Heading2', parent=styles['Heading2'], fontSize=14, leading=18, spaceAfter=10))
styles.add(ParagraphStyle(name='Normal', parent=styles['Normal'], fontSize=10, leading=12, alignment=TA_JUSTIFY))

story = []
for line in lines:
    stripped = line.strip('\n')
    if stripped.startswith('# '):
        story.append(Paragraph(stripped[2:], styles['Heading1']))
        story.append(Spacer(1, 6))
    elif stripped.startswith('## '):
        story.append(Paragraph(stripped[3:], styles['Heading2']))
        story.append(Spacer(1, 4))
    elif stripped == '---':
        story.append(Spacer(1, 12))
        story.append(PageBreak())
    else:
        if stripped:
            story.append(Paragraph(stripped, styles['Normal']))
            story.append(Spacer(1, 2))
        else:
            story.append(Spacer(1, 4))

# Build PDF
doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
doc.build(story)
print(f"PDF generated at {pdf_path}")
