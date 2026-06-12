import pytest
from backend.utils.crawler import extract_clean_text_from_html

def test_extract_clean_text_basic():
    html = "<html><body><div><p>This is a normal paragraph with some descriptive text about a startup.</p></div></body></html>"
    text = extract_clean_text_from_html(html)
    assert "descriptive text about a startup" in text

def test_extract_clean_text_boilerplate_removal():
    html = """
    <html>
        <body>
            <div><p>We use cookies to improve your experience on our website. Please agree to our terms.</p></div>
            <div><p>This is a valid startup description block that should not be removed.</p></div>
            <div><p>Click here to subscribe to our newsletter for more updates.</p></div>
        </body>
    </html>
    """
    text = extract_clean_text_from_html(html)
    # The boilerplate blocks should be filtered out
    assert "use cookies" not in text.lower()
    assert "subscribe" not in text.lower()
    assert "valid startup description block" in text

def test_extract_clean_text_link_density():
    html = """
    <html>
        <body>
            <!-- Navigation block with high link density -->
            <div>
                <a href="/home">Home</a> | 
                <a href="/about">About Us</a> | 
                <a href="/contact">Contact Us</a> | 
                <a href="/blog">Blog</a>
            </div>
            <!-- Content block with low link density -->
            <div>
                <p>SecurePay is a fintech startup that provides automated fraud detection and claims security software.</p>
            </div>
        </body>
    </html>
    """
    text = extract_clean_text_from_html(html)
    assert "Home" not in text
    assert "About Us" not in text
    assert "SecurePay is a fintech startup" in text

def test_extract_clean_text_decomposes():
    html = """
    <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log("hello");</script>
        </head>
        <body>
            <header>Welcome to our site</header>
            <div><p>This is the actual page content that matters.</p></div>
            <footer>© 2026 Startup Inc. All rights reserved.</footer>
        </body>
    </html>
    """
    text = extract_clean_text_from_html(html)
    assert "console.log" not in text
    assert "body { color: red; }" not in text
    assert "Welcome to our site" not in text
    assert "actual page content that matters" in text
