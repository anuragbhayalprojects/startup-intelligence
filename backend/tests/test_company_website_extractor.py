import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.scrapers.company_website.extractor import CompanyWebsiteExtractor, CompanyProfileSchema

@pytest.mark.anyio
async def test_load_config():
    extractor = CompanyWebsiteExtractor()
    assert extractor.config is not None
    assert "client" in extractor.config
    assert "link_discovery" in extractor.config

def test_clean_html():
    extractor = CompanyWebsiteExtractor()
    raw_html = "<html><head><style>body {color: red;}</style></head><body><nav>Menu</nav><script>console.log(1);</script><h1>Eka Care</h1><p>AI OS.</p></body></html>"
    cleaned = extractor.clean_html(raw_html)
    assert "Menu" not in cleaned
    assert "console.log" not in cleaned
    assert "Eka Care AI OS." in cleaned

def test_route_links_to_buckets():
    extractor = CompanyWebsiteExtractor()
    homepage_html = """
    <html>
      <body>
        <a href="/about-us">About Us</a>
        <a href="https://www.eka.care/products/emr">EMR Suite</a>
        <a href="/contact">Contact</a>
        <a href="https://google.com">External Link</a>
      </body>
    </html>
    """
    buckets = extractor.route_links_to_buckets("https://www.eka.care", homepage_html)
    assert len(buckets["identity"]) >= 1
    assert "https://www.eka.care/about-us" in buckets["identity"]
    assert len(buckets["offerings"]) >= 1
    assert "https://www.eka.care/products/emr" in buckets["offerings"]
    assert len(buckets["corporate"]) >= 1
    assert "https://www.eka.care/contact" in buckets["corporate"]

def test_extract_bm25_chunks():
    extractor = CompanyWebsiteExtractor()
    texts = [
        "Eka Care is a health tech startup developing a digital Health OS for modern clinics.",
        "The founders are Vikalp Sahni and Deepak Tuli who established the startup in Bangalore."
    ]
    product_chunk = extractor.extract_bm25_chunks(texts, "health tech digital clinic", 1000)
    assert "digital Health OS" in product_chunk

    founder_chunk = extractor.extract_bm25_chunks(texts, "founders Vikalp Deepak", 1000)
    assert "Vikalp Sahni" in founder_chunk

@pytest.mark.anyio
@patch("backend.scrapers.company_website.extractor.search_duckduckgo")
async def test_execute_precision_fallbacks(mock_search):
    extractor = CompanyWebsiteExtractor()
    # Mock DuckDuckGo results for corporate details and founder linkedin
    mock_search.side_effect = lambda q: (
        "https://in.linkedin.com/company/ekacare" if "LinkedIn company page" in q else
        "Orbi Health Pvt Ltd established in 2020 headquartered in Bangalore India" if "legal registration details" in q else
        "https://in.linkedin.com/in/vikalpsahni" if "Vikalp Sahni" in q else ""
    )

    current_data = {
        "company_name": "Eka Care",
        "legal_name": None,
        "aliases": [],
        "website_url": "https://www.eka.care",
        "company_linkedin_url": None,
        "founding_year": None,
        "headquarters": {
            "address": None, "city": None, "state": None, "country": None
        },
        "leadership": [
            {"name": "Vikalp Sahni", "role": "Founder", "brief_background": None, "linkedin_url": None}
        ]
    }

    # Mock gateway
    mock_gateway_res = MagicMock()
    mock_gateway_res.content = {
        "legal_name": "Orbi Health Pvt Ltd",
        "founding_year": 2020,
        "headquarters": {
            "address": "Bangalore",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India"
        }
    }
    
    with patch.object(extractor.gateway, "route", AsyncMock(return_value=mock_gateway_res)):
        patched = await extractor.execute_precision_fallbacks(current_data, "Eka Care")
        
        assert patched["company_linkedin_url"] == "https://in.linkedin.com/company/ekacare"
        assert patched["legal_name"] == "Orbi Health Pvt Ltd"
        assert patched["founding_year"] == 2020
        assert patched["headquarters"]["city"] == "Bangalore"
        assert patched["leadership"][0]["linkedin_url"] == "https://in.linkedin.com/in/vikalpsahni"

@pytest.mark.anyio
@patch("backend.scrapers.company_website.extractor.CompanyWebsiteExtractor.scrape_single_page")
@patch("backend.scrapers.company_website.extractor.search_duckduckgo")
async def test_full_extract_flow(mock_search, mock_scrape):
    mock_scrape.return_value = "<html><body><h1>Eka Care</h1><p>Digital Health OS platform.</p></body></html>"
    mock_search.return_value = ""

    extractor = CompanyWebsiteExtractor()
    
    # Mock AIGateway
    mock_corp_res = MagicMock()
    mock_corp_res.content = {
        "legal_name": "Orbi Health Pvt Ltd",
        "founding_year": 2020,
        "aliases": ["EkaCare"],
        "website_url": "https://www.eka.care",
        "company_linkedin_url": "https://in.linkedin.com/company/ekacare",
        "headquarters": {"address": "Bangalore", "city": "Bangalore", "state": "Karnataka", "country": "India"},
        "leadership": [{"name": "Vikalp Sahni", "role": "Founder", "brief_background": None, "linkedin_url": None}]
    }
    
    mock_prod_res = MagicMock()
    mock_prod_res.content = {
        "list_data": [
            {"name": "Eka EMR", "category": "Software", "description": "Clinic operating system", "target_customer": "Doctors", "deployment_model": "SaaS"}
        ]
    }

    async def mock_route(req):
        if "corporate intelligence" in req.prompt:
            return mock_corp_res
        return mock_prod_res

    with patch.object(extractor.gateway, "route", AsyncMock(side_effect=mock_route)):
        profile = await extractor.extract("Eka Care", "https://www.eka.care")
        
        assert isinstance(profile, CompanyProfileSchema)
        assert profile.company_name == "Eka Care"
        assert profile.legal_name == "Orbi Health Pvt Ltd"
        assert len(profile.products_and_solutions) == 1
        assert profile.products_and_solutions[0].name == "Eka EMR"
