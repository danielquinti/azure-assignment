import os
import markdown
from xhtml2pdf import pisa

# Go to the script's directory to ensure paths match
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 1. Read Markdown file
with open("readme.md", "r", encoding="utf-8") as f:
    md_content = f.read()

# 2. Convert Markdown to HTML
html_content = markdown.markdown(
    md_content,
    extensions=['extra', 'codehilite']
)

# 3. Add styling (especially styling code blocks, blockquotes, tables, and images)
html_with_style = f"""
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{
        size: a4;
        margin: 2cm;
    }}
    body {{
        font-family: Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.6;
        color: #333;
    }}
    h1 {{
        font-size: 20pt;
        color: #0056b3;
        border-bottom: 2px solid #0056b3;
        padding-bottom: 5px;
        margin-top: 0;
        margin-bottom: 20px;
    }}
    h2 {{
        font-size: 14pt;
        color: #0056b3;
        margin-top: 30px;
        margin-bottom: 10px;
        border-bottom: 1px solid #ddd;
        padding-bottom: 3px;
    }}
    h3 {{
        font-size: 11pt;
        color: #333;
        margin-top: 20px;
        margin-bottom: 8px;
    }}
    p {{
        margin-bottom: 12px;
        text-align: justify;
    }}
    ul, ol {{
        margin-top: 5px;
        margin-bottom: 15px;
        padding-left: 20px;
    }}
    li {{
        margin-bottom: 5px;
    }}
    pre {{
        background-color: #f7f7f9;
        border: 1px solid #e1e1e8;
        border-radius: 3px;
        padding: 10px;
        font-family: "Courier New", Courier, monospace;
        font-size: 8.5pt;
        margin-bottom: 15px;
    }}
    code {{
        font-family: "Courier New", Courier, monospace;
        background-color: #f7f7f9;
        color: #d72b3f;
        font-size: 9pt;
        padding: 2px 4px;
        border-radius: 3px;
    }}
    pre code {{
        background-color: transparent;
        color: inherit;
        padding: 0;
    }}
    blockquote {{
        border-left: 4px solid #0056b3;
        background-color: #f0f7ff;
        padding: 10px 15px;
        margin: 15px 0;
        color: #555;
    }}
    img {{
        max-width: 100%;
        height: auto;
        display: block;
        margin: 15px auto;
        border: 1px solid #ccc;
    }}
    hr {{
        border: 0;
        border-top: 1px solid #eee;
        margin: 30px 0;
    }}
    a {{
        color: #0056b3;
        text-decoration: none;
    }}
</style>
</head>
<body>
    {html_content}
</body>
</html>
"""

# 4. Save to PDF
output_pdf_path = "readme.pdf"
with open(output_pdf_path, "w+b") as out_file:
    pisa_status = pisa.CreatePDF(html_with_style, dest=out_file)

if pisa_status.err == 0:
    print(f"PDF generated successfully at: {os.path.abspath(output_pdf_path)}")
else:
    print("Error generating PDF:", pisa_status.err)
