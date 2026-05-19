import os
import markdown

md_path = os.path.join(os.path.dirname(__file__), 'PROJECT_OVERVIEW.md')
html_path = os.path.join(os.path.dirname(__file__), 'PROJECT_OVERVIEW.html')

with open(md_path, 'r', encoding='utf-8') as f:
    text = f.readlines()
    # Strip some of the pandoc specific lines I added at the end
    clean_text = "".join([line for line in text if 'pandoc' not in line])

html_body = markdown.markdown(clean_text, extensions=['tables'])

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #333;
            line-height: 1.6;
            margin: 0;
            padding: 40px;
        }}
        h1 {{
            color: #2563EB;
            font-size: 28px;
            border-bottom: 2px solid #93C5FD;
            padding-bottom: 8px;
        }}
        h2 {{
            color: #1F2937;
            font-size: 22px;
            margin-top: 30px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #D1D5DB;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #F3F4F6;
            color: #1F2937;
            font-weight: 600;
        }}
        code {{
            background-color: #F3F4F6;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: Consolas, monospace;
            font-size: 14px;
        }}
        pre {{
            background-color: #F3F4F6;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        ul, ol {{
            margin-bottom: 20px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        @page {{
            margin: 1.5cm;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f"Generated HTML at {html_path}")
