import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

# Paths – use the proper repository location (no leading spaces)
base_dir = r'd:\Minor Project\Neurology-3D-Viz-Engine-master'
md_path = os.path.join(base_dir, 'PROJECT_OVERVIEW.md')
pdf_path = os.path.join(base_dir, 'PROJECT_OVERVIEW.pdf')

if not os.path.exists(md_path):
    raise FileNotFoundError(f"Markdown source not found: {md_path}")

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

styles = getSampleStyleSheet()
story = []
for line in lines:
    txt = line.rstrip('\n')
    if txt.startswith('# '):
        story.append(Paragraph(txt[2:], styles['Heading1']))
        story.append(Spacer(1, 6))
    elif txt.startswith('## '):
        story.append(Paragraph(txt[3:], styles['Heading2']))
        story.append(Spacer(1, 4))
    elif txt == '---':
        story.append(PageBreak())
    else:
        if txt:
            story.append(Paragraph(txt, styles['Normal']))
            story.append(Spacer(1, 2))
        else:
            story.append(Spacer(1, 4))

doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
doc.build(story)
print(f"PDF generated at {pdf_path}")
