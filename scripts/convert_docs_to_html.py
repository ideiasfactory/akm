import markdown
from pathlib import Path

def convert_md_to_html(md_file: str, html_file: str, title: str):
    """Convert markdown file to styled HTML"""
    
    # Read markdown content
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )
    
    # Create full HTML page with styling
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - API Key Management Service</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary: #667eea;
            --secondary: #764ba2;
            --accent: #f093fb;
            --dark: #1a1a2e;
            --light: #f8f9fa;
            --code-bg: #282c34;
            --border: #e0e0e0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .nav {{
            background: var(--dark);
            padding: 15px 40px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}

        .nav a {{
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 5px;
            transition: all 0.3s ease;
        }}

        .nav a:hover {{
            background: var(--primary);
            transform: translateY(-2px);
        }}

        .content {{
            padding: 40px;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: var(--dark);
            margin: 30px 0 15px 0;
            line-height: 1.3;
        }}

        h1 {{ font-size: 2.5em; border-bottom: 3px solid var(--primary); padding-bottom: 10px; }}
        h2 {{ font-size: 2em; border-bottom: 2px solid var(--border); padding-bottom: 8px; margin-top: 40px; }}
        h3 {{ font-size: 1.5em; color: var(--primary); }}
        h4 {{ font-size: 1.3em; }}

        p {{
            margin: 15px 0;
            line-height: 1.8;
        }}

        a {{
            color: var(--primary);
            text-decoration: none;
            border-bottom: 1px dotted var(--primary);
        }}

        a:hover {{
            color: var(--secondary);
            border-bottom: 1px solid var(--secondary);
        }}

        code {{
            background: #f4f4f4;
            padding: 3px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}

        pre {{
            background: var(--code-bg);
            color: #abb2bf;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
            border-left: 4px solid var(--primary);
        }}

        pre code {{
            background: none;
            color: inherit;
            padding: 0;
            font-size: 0.95em;
        }}

        blockquote {{
            border-left: 4px solid var(--primary);
            padding: 15px 20px;
            margin: 20px 0;
            background: #f8f9fa;
            font-style: italic;
        }}

        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}

        li {{
            margin: 8px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}

        .success {{
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}

        .info {{
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}

        .footer {{
            background: var(--dark);
            color: white;
            padding: 30px 40px;
            text-align: center;
        }}

        .footer a {{
            color: var(--accent);
            border-bottom: 1px dotted var(--accent);
        }}

        .back-to-top {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--primary);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            text-decoration: none;
            font-size: 24px;
        }}

        .back-to-top:hover {{
            background: var(--secondary);
            transform: translateY(-5px);
        }}

        @media (max-width: 768px) {{
            .container {{
                border-radius: 0;
            }}

            .header {{
                padding: 30px 20px;
            }}

            .header h1 {{
                font-size: 2em;
            }}

            .nav {{
                padding: 15px 20px;
            }}

            .content {{
                padding: 20px;
            }}

            pre {{
                padding: 15px;
                font-size: 0.85em;
            }}
        }}

        /* Syntax highlighting for code blocks */
        .codehilite .k {{ color: #c678dd; }} /* keyword */
        .codehilite .s {{ color: #98c379; }} /* string */
        .codehilite .n {{ color: #e06c75; }} /* name */
        .codehilite .c {{ color: #5c6370; font-style: italic; }} /* comment */
        .codehilite .m {{ color: #d19a66; }} /* number */
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 {title}</h1>
            <p>API Key Management Service</p>
        </div>

        <div class="nav">
            <a href="/">🏠 Home</a>
            <a href="/quickstart">🚀 Quick Start</a>
            <a href="/administration">🔐 Administration</a>
            <a href="/docs">📚 API Docs</a>
            <a href="/redoc">📖 ReDoc</a>
        </div>

        <div class="content">
{html_content}
        </div>

        <div class="footer">
            <p>Built with ❤️ using FastAPI, PostgreSQL, and SQLAlchemy</p>
            <p style="margin-top: 10px;">© 2025 API Key Management Service by <a href="https://github.com/ideiasfactory" target="_blank">Ideias Factory</a></p>
        </div>
    </div>

    <a href="#" class="back-to-top">↑</a>

    <script>
        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {{
                    target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }});
        }});

        // Back to top button
        const backToTop = document.querySelector('.back-to-top');
        window.addEventListener('scroll', () => {{
            if (window.pageYOffset > 300) {{
                backToTop.style.display = 'flex';
            }} else {{
                backToTop.style.display = 'none';
            }}
        }});

        backToTop.addEventListener('click', (e) => {{
            e.preventDefault();
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }});
    </script>
</body>
</html>"""
    
    # Write HTML file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ Converted {md_file} → {html_file}")

if __name__ == "__main__":
    # Convert QUICKSTART.md
    convert_md_to_html(
        "docs/QUICKSTART.md",
        "public/quickstart.html",
        "Quick Start Guide"
    )
    
    # Convert ADMINISTRATION.md
    convert_md_to_html(
        "docs/ADMINISTRATION.md",
        "public/administration.html",
        "Administration Guide"
    )
    
    # Convert API_VERSIONING.md
    convert_md_to_html(
        "docs/API_VERSIONING.md",
        "public/api-versioning.html",
        "API Versioning Guide"
    )
    
    # Convert AUTHENTICATION.md
    convert_md_to_html(
        "docs/AUTHENTICATION.md",
        "public/authentication.html",
        "Authentication Guide"
    )
    
    # Convert API_KEY_MANAGEMENT.md
    convert_md_to_html(
        "docs/API_KEY_MANAGEMENT.md",
        "public/api-key-management.html",
        "API Key Management Guide"
    )
    
    # Convert DEPLOYMENT.md
    convert_md_to_html(
        "docs/DEPLOYMENT.md",
        "public/deployment.html",
        "Deployment Guide"
    )
    
    # Convert TESTING.md
    convert_md_to_html(
        "docs/TESTING.md",
        "public/testing.html",
        "Testing Guide"
    )
    
    print("✅ All conversions completed!")
