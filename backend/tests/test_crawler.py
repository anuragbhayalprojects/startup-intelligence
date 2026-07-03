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

def test_scrape_page_basic():
    from backend.utils.crawler import scrape_page
    res = scrape_page("https://example.com")
    assert "SecurePay is a fintech startup" in res["text_content"]

def test_scrape_page_extracts_social_links_and_legal_name():
    from unittest.mock import patch, MagicMock
    from backend.utils.crawler import scrape_page
    
    mock_html = """
    <html>
        <body>
            <p>Welcome to Acme platform!</p>
            <a href="https://linkedin.com/company/acme-technologies-pvt-ltd">LinkedIn</a>
            <a href="https://twitter.com/acme_tech">Twitter</a>
            <a href="https://linkedin.com/in/john-doe-founder">John Doe profile</a>
            <footer>
                <div class="copyright">© 2026 Acme Technologies Private Limited. All rights reserved.</div>
            </footer>
        </body>
    </html>
    """
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = mock_html
    
    with patch("backend.utils.crawler.requests.get", return_value=mock_resp):
        res = scrape_page("https://acme-test.com")
        
        # Verify metadata extracted before tag decomposition
        assert res["legal_company_name"] == "Acme Technologies Private Limited"
        assert res["social_links"]["linkedin"] == "https://linkedin.com/company/acme-technologies-pvt-ltd"
        assert res["social_links"]["twitter"] == "https://twitter.com/acme_tech"
        assert "https://linkedin.com/in/john-doe-founder" in res["social_links"]["linkedin_profiles"]


def test_crawl_product_pages_dynamic():
    from unittest.mock import patch, MagicMock
    import importlib
    import backend.utils.crawler
    
    # Reload the module to bypass conftest autouse mock of crawl_product_pages
    importlib.reload(backend.utils.crawler)
    
    mock_homepage_html = """
    <html>
        <body>
            <a href="/personal-loan">Personal Loan Products</a>
            <a href="/instant-loans-online/1000-instant-loan">Instant Loan Online</a>
            <a href="/about-us">About Acme</a>
            <a href="/contact-us">Contact Us</a>
            <a href="https://external-domain.com/some-page">External Site</a>
        </body>
    </html>
    """
    
    mock_product_page_html = """
    <html>
        <body>
            <p>Acme Personal Loan is low-interest and high speed. We provide excellent customer service and flexible repayment terms for all qualified applicants across the country.</p>
        </body>
    </html>
    """
    
    mock_about_page_html = """
    <html>
        <body>
            <p>This is the unique About Us page body content. Acme is founded in 2026.</p>
        </body>
    </html>
    """
    
    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "personal-loan" in url or "instant-loan" in url:
            resp.text = mock_product_page_html
        elif "about" in url:
            resp.text = mock_about_page_html
        else:
            resp.text = mock_homepage_html
        return resp
        
    with patch("backend.utils.crawler.requests.get", side_effect=mock_get):
        collected_text = backend.utils.crawler.crawl_product_pages("https://acme-loans.com")
        
        # Check that the dynamic paths were crawled and appended
        assert "Acme Personal Loan is low-interest" in collected_text
        # Check that excluded paths like /about-us were NOT crawled
        assert "unique About Us page body" not in collected_text


