import os
import re
import json
import asyncio
import logging
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi

from backend.ai.gateway.ai_gateway import AIGateway
from backend.ai.types import AIRequest
from backend.utils.search import search_duckduckgo

# Setup logger
logger = logging.getLogger("startup_intelligence.scrapers.company_website")

# -----------------------------------------------------------------------------
# 1. Pydantic Output Schemas
# -----------------------------------------------------------------------------

class HeadquartersSchema(BaseModel):
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="Headquarters city")
    state: Optional[str] = Field(None, description="Headquarters state/province")
    country: Optional[str] = Field(None, description="Headquarters country")

class ProductSchema(BaseModel):
    name: str = Field(..., description="Product name")
    category: Optional[str] = Field(None, description="Product category or type")
    description: str = Field(..., description="Description of product")
    target_customer: Optional[str] = Field(None, description="Target customer segment")
    deployment_model: Optional[str] = Field(None, description="SaaS / On-premise / API / etc")

class LeaderSchema(BaseModel):
    name: str = Field(..., description="Founder or leadership name")
    role: str = Field(..., description="Role/Designation")
    brief_background: Optional[str] = Field(None, description="Brief background details")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")

class CompanyProfileSchema(BaseModel):
    company_name: str = Field(..., description="Operating brand name")
    legal_name: Optional[str] = Field(None, description="Registered legal name")
    aliases: List[str] = Field(default_factory=list, description="Other names or spelling variations")
    website_url: str = Field(..., description="Website URL")
    company_linkedin_url: Optional[str] = Field(None, description="Company LinkedIn page URL")
    founding_year: Optional[int] = Field(None, description="Year established")
    one_liner: Optional[str] = Field(None, description="Concise one-liner summary")
    description: Optional[str] = Field(None, description="Detailed company description")
    business_model: Optional[str] = Field(None, description="Primary business model category")
    target_audience: Optional[str] = Field(None, description="Description of target customers/consumers")
    industry: Optional[str] = Field(None, description="Industry category")
    sector: Optional[str] = Field(None, description="Sector category")
    subsector: Optional[str] = Field(None, description="Subsector category")
    tags: List[str] = Field(default_factory=list, description="Keywords/descriptors")
    business_models: List[str] = Field(default_factory=list, description="List of specific business models")
    headquarters: HeadquartersSchema = Field(default_factory=HeadquartersSchema)
    products_and_solutions: List[ProductSchema] = Field(default_factory=list)
    leadership: List[LeaderSchema] = Field(default_factory=list)

# -----------------------------------------------------------------------------
# 2. Main Extractor Class
# -----------------------------------------------------------------------------

class CompanyWebsiteExtractor:
    def __init__(self):
        self.gateway = AIGateway()
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config",
            "scraper_config.json"
        )
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load scraper_config.json: {e}")
            
        # Fallback default configuration
        return {
            "client": {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "timeout_seconds": 10,
                "min_body_characters": 600
            },
            "link_discovery": {
                "identity_bucket": {
                    "keywords": ["team", "about", "leadership", "founders", "management", "history", "who-we-are"],
                    "max_urls": 2
                },
                "offerings_bucket": {
                    "keywords": ["products", "solutions", "features", "platform", "pricing", "software", "services", "collections", "shop", "menu", "catalog", "catalogue", "items"],
                    "max_urls": 7
                },
                "corporate_bucket": {
                    "keywords": ["contact", "contact-us", "privacy", "legal", "compliance", "terms", "terms-of-service", "office", "address"],
                    "max_urls": 1
                }
            },
            "bm25_settings": {
                "chunk_size_chars": 1000,
                "chunk_overlap_chars": 200,
                "character_budget_per_pass": 4000
            }
        }

    async def scrape_single_page(self, url: str) -> str:
        """Asynchronously scrapes a single web page, falling back to Playwright if needed."""
        client_cfg = self.config.get("client", {})
        ua = client_cfg.get("user_agent", "")
        timeout = client_cfg.get("timeout_seconds", 10)
        min_chars = client_cfg.get("min_body_characters", 600)
        
        headers = {"User-Agent": ua}
        html_content = ""
        
        # Phase 1: Attempt fast curl_cffi fetch
        loop = asyncio.get_event_loop()
        try:
            def fetch():
                try:
                    from curl_cffi import requests as curl_requests
                    resp = curl_requests.get(url, impersonate="chrome120", headers=headers, timeout=timeout)
                    return resp.text if resp.status_code == 200 else ""
                except (ImportError, TypeError):
                    import requests as requests_lib
                    resp = requests_lib.get(url, headers=headers, timeout=timeout)
                    return resp.text if resp.status_code == 200 else ""
            
            html_content = await loop.run_in_executor(None, fetch)
        except Exception as e:
            logger.debug(f"Fast curl_cffi scrape failed for {url}: {e}")
            
        # Parse text length and clean indicators
        soup = BeautifulSoup(html_content, "html.parser") if html_content else None
        text_len = len(soup.get_text(" ", strip=True)) if soup else 0
        
        js_indicator = False
        if soup:
            # Check for standard js indicators
            js_indicator = bool(soup.find("noscript") or "javascript" in html_content.lower() and text_len < min_chars)
            
        # Phase 2: Fallback to async headless Playwright if raw fetch is empty/short or SPA detected
        if text_len < min_chars or js_indicator:
            logger.info(f"🔄 Triggering Playwright headless fallback for {url} (Length={text_len}, JS_Ind={js_indicator})...")
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(user_agent=ua)
                    page = await context.new_page()
                    await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
                    html_content = await page.content()
                    await browser.close()
            except Exception as pe:
                logger.warning(f"Playwright fallback failed for {url}: {pe}")
                
        return html_content

    def clean_html(self, html: str) -> str:
        """Strips layout wrappers and cleans boilerplate from raw HTML."""
        if not html:
            return ""
        try:
            soup = BeautifulSoup(html, "html.parser")
            # Remove non-semantic nodes (preserving footers for legal details and social links)
            for node in soup.find_all(["script", "style", "nav", "header", "svg", "noscript"]):
                node.decompose()
                
            # Remove cookie consent banners/modals
            for banner in soup.find_all(class_=re.compile(r"cookie|consent|banner|modal|overlay|popup", re.I)):
                banner.decompose()
                
            text = soup.get_text(" ", strip=True)
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except Exception as e:
            logger.warning(f"HTML cleanup failed: {e}")
            return ""

    def route_links_to_buckets(self, homepage_url: str, html: str) -> Dict[str, List[str]]:
        """Parses local anchor links and distributes them into buckets based on config keywords."""
        buckets_cfg = self.config.get("link_discovery", {})
        buckets = {
            "identity": [],
            "offerings": [],
            "corporate": []
        }
        
        if not html:
            return buckets
            
        soup = BeautifulSoup(html, "html.parser")
        parsed_root = urllib.parse.urlparse(homepage_url)
        root_domain = parsed_root.netloc.replace("www.", "")
        
        seen_urls = {homepage_url.rstrip("/")}
        
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
                
            # Convert to absolute URL
            abs_url = urllib.parse.urljoin(homepage_url, href)
            # Ensure it is in the same domain
            parsed_abs = urllib.parse.urlparse(abs_url)
            abs_domain = parsed_abs.netloc.replace("www.", "")
            
            if root_domain not in abs_domain:
                continue
                
            clean_url = abs_url.rstrip("/")
            if clean_url in seen_urls:
                continue
                
            seen_urls.add(clean_url)
            
            # Analyze path and link text to route to correct bucket
            link_text = anchor.get_text(" ", strip=True).lower()
            path_lower = parsed_abs.path.lower()
            combined_match = f"{link_text} {path_lower}"
            
            # Check matches across buckets
            matched = False
            for bucket_key, cfg_key in [("identity", "identity_bucket"), ("offerings", "offerings_bucket"), ("corporate", "corporate_bucket")]:
                keywords = buckets_cfg.get(cfg_key, {}).get("keywords", [])
                max_urls = buckets_cfg.get(cfg_key, {}).get("max_urls", 5)
                
                if len(buckets[bucket_key]) >= max_urls:
                    continue
                    
                if any(kw in combined_match for kw in keywords):
                    buckets[bucket_key].append(abs_url)
                    matched = True
                    break
                    
        return buckets

    def extract_bm25_chunks(self, pages: List[Any], query: str, budget_chars: int) -> str:
        """Splits raw page text into chunks and retrieves the top chunks matching query using BM25."""
        if not pages:
            return ""
            
        bm_cfg = self.config.get("bm25_settings", {})
        chunk_size = bm_cfg.get("chunk_size_chars", 1000)
        overlap = bm_cfg.get("chunk_overlap_chars", 200)
        
        chunks = []  # List of tuples: (chunk_text, page_url)
        for item in pages:
            if not item:
                continue
            
            # Support backward compatibility if it is raw string list
            if isinstance(item, str):
                text = item
                url = None
            else:
                text = item.get("text", "")
                url = item.get("url", "")
                
            if not text:
                continue
                
            i = 0
            while i < len(text):
                chunk_text = text[i:i + chunk_size].strip()
                if chunk_text:
                    # Avoid duplicate text blocks
                    if not any(c[0] == chunk_text for c in chunks):
                        chunks.append((chunk_text, url))
                i += (chunk_size - overlap)
                
        if not chunks:
            return ""
            
        # Initialize BM25Okapi
        import time
        start_time = time.perf_counter()
        
        tokenized_corpus = [c[0].lower().split() for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Tokenize query
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        
        # Pair chunk with score and sort using term overlap as tie-breaker
        chunk_scores = sorted(
            zip(chunks, scores),
            key=lambda x: (
                x[1],
                sum(1 for term in tokenized_query if term in x[0][0].lower())
            ),
            reverse=True
        )
        
        selected_chunks = []
        current_len = 0
        max_chunks = bm_cfg.get("max_chunks_selected", 5)
        
        for (chunk_text, url), score in chunk_scores:
            if score == 0.0 and selected_chunks:
                continue
                
            if len(selected_chunks) >= max_chunks:
                break
            
            # Format the chunk with header if url is provided
            if url:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path.strip("/")
                page_name = path if path else "homepage"
                header = f"\n--- SOURCED FROM: '{page_name}' page ({url}) ---\n"
                formatted_chunk = header + chunk_text
            else:
                formatted_chunk = chunk_text
                
            if current_len + len(formatted_chunk) > budget_chars:
                if not selected_chunks:  # Add at least one chunk even if it exceeds budget
                    selected_chunks.append(formatted_chunk)
                break
            selected_chunks.append(formatted_chunk)
            current_len += len(formatted_chunk)
            
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Log BM25 call to prompt ledger for observability
        try:
            from backend.utils.tracing import log_prompt_ledger
            first_word = query.split()[0].upper() if query else "QUERY"
            indexed_str_list = [f"[{c[1] or 'unknown'}]: {c[0]}" for c in chunks]
            log_prompt_ledger(
                prompt_id=f"BM25_{first_word}",
                agent_name="BM25_RETRIEVER",
                prompt_template=f"BM25 Query: '{query}'",
                injected_context=f"Indexed Chunks (Total={len(chunks)}):\n" + "\n---\n".join(indexed_str_list),
                raw_response=f"Selected Chunks (Total={len(selected_chunks)}):\n" + "\n---\n".join(selected_chunks),
                parsed_response={"query": query, "num_indexed": len(chunks), "num_selected": len(selected_chunks)},
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.debug(f"Failed to log BM25 pass to observability: {e}")
            
        return "\n\n".join(selected_chunks)

    async def _call_ai_gateway(self, prompt_template_path: str, context: str, company_name: str) -> dict:
        """Renders prompts and requests JSON parsing from AIGateway."""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts",
            prompt_template_path
        )
        
        try:
            with open(prompt_path, "r") as f:
                template = f.read()
        except Exception as e:
            logger.error(f"Failed to read prompt template {prompt_template_path}: {e}")
            return {}
            
        # Simple template formatting
        prompt = template.replace("{{ company_name }}", company_name).replace("{{ source_context }}", context)
        
        req = AIRequest(
            prompt=prompt,
            task="enrichment_identity",
            json_format=True,
            num_ctx=6000,
            agent_name="CompanyWebsiteExtractor"
        )
        
        try:
            response = await self.gateway.route(req)
            if response and response.content:
                if isinstance(response.content, dict):
                    return response.content
                elif isinstance(response.content, list):
                    return {"list_data": response.content}
                elif isinstance(response.content, str):
                    cleaned = response.content.strip()
                    # Strip markdown blocks
                    if cleaned.startswith("```"):
                        cleaned = re.sub(r"^```(?:json)?\n|```$", "", cleaned, flags=re.M).strip()
                    return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"AIGateway call failed for {prompt_template_path}: {e}")
            
        return {}

    async def execute_precision_fallbacks(self, current_data: dict, company_name: str) -> dict:
        """Analyzes missing fields and triggers fallback search lookup logic to patch nulls."""
        patched_data = json.loads(json.dumps(current_data))
        loop = asyncio.get_event_loop()
        
        # 1. Company LinkedIn Page URL fallback
        if not patched_data.get("company_linkedin_url"):
            query = f"{company_name} LinkedIn company page"
            logger.info(f"🔍 [Fallback] Searching for Company LinkedIn: '{query}'")
            search_results = await loop.run_in_executor(None, search_duckduckgo, query)
            match = re.search(r"(https?://[a-z]{2,3}\.linkedin\.com/company/[a-zA-Z0-9_-]+)", search_results)
            if match:
                patched_data["company_linkedin_url"] = match.group(1)
                logger.info(f"✅ Patched Company LinkedIn: {patched_data['company_linkedin_url']}")

        # 2. Corporate details fallback (Legal name, headquarters, founding year)
        hq = patched_data.get("headquarters") or {}
        missing_corp = (
            not patched_data.get("legal_name") or
            not patched_data.get("founding_year") or
            not hq.get("city") or
            not hq.get("country")
        )
        if missing_corp:
            query = f"\"{company_name}\" legal registration details corporate office address founding year"
            logger.info(f"🔍 [Fallback] Searching for corporate metrics: '{query}'")
            search_results = await loop.run_in_executor(None, search_duckduckgo, query)
            
            prompt = (
                f"From the search results below, extract the registered legal name, founding year, and headquarters details (address, city, state, country) for '{company_name}'.\n\n"
                f"Search Results:\n{search_results[:3000]}\n\n"
                f"Return ONLY a valid JSON object matching this schema:\n"
                f"{{\n  \"legal_name\": \"string or null\",\n  \"founding_year\": integer or null,\n"
                f"  \"headquarters\": {{\n    \"address\": \"string or null\",\n    \"city\": \"string or null\",\n    \"state\": \"string or null\",\n    \"country\": \"string or null\"\n  }}\n}}"
            )
            req = AIRequest(
                prompt=prompt,
                task="enrichment_identity",
                json_format=True,
                num_ctx=4000,
                agent_name="CompanyWebsiteExtractor"
            )
            try:
                response = await self.gateway.route(req)
                resp_content = response.content
                if isinstance(resp_content, str):
                    cleaned = resp_content.strip()
                    if cleaned.startswith("```"):
                        cleaned = re.sub(r"^```(?:json)?\n|```$", "", cleaned, flags=re.M).strip()
                    resp_content = json.loads(cleaned)
                
                if isinstance(resp_content, dict):
                    if not patched_data.get("legal_name") and resp_content.get("legal_name"):
                        patched_data["legal_name"] = resp_content["legal_name"]
                    if not patched_data.get("founding_year") and resp_content.get("founding_year"):
                        patched_data["founding_year"] = int(resp_content["founding_year"])
                        
                    fallback_hq = resp_content.get("headquarters") or {}
                    if isinstance(fallback_hq, dict):
                        for k in ["address", "city", "state", "country"]:
                            if not hq.get(k) and fallback_hq.get(k):
                                if "headquarters" not in patched_data or not patched_data["headquarters"]:
                                    patched_data["headquarters"] = {}
                                patched_data["headquarters"][k] = fallback_hq[k]
                    logger.info(f"✅ Patched Corporate details successfully.")
            except Exception as e:
                logger.warning(f"Corporate details fallback completion failed: {e}")

        # 3. Leadership profiles fallback
        leaders = patched_data.get("leadership") or []
        if not leaders:
            query = f"\"{company_name}\" founders co-founders CEO leadership team"
            logger.info(f"🔍 [Fallback] Searching for leadership: '{query}'")
            search_results = await loop.run_in_executor(None, search_duckduckgo, query)
            prompt = (
                f"From the search results below, extract the list of founders and key leadership for '{company_name}'.\n\n"
                f"Search Results:\n{search_results[:3000]}\n\n"
                f"Return ONLY a valid JSON list matching this schema:\n"
                f"[\n  {{\n    \"name\": \"string\",\n    \"role\": \"string\",\n    \"brief_background\": \"string or null\",\n    \"linkedin_url\": \"string or null\"\n  }}\n]"
            )
            req = AIRequest(
                prompt=prompt,
                task="enrichment_identity",
                json_format=True,
                num_ctx=4000,
                agent_name="CompanyWebsiteExtractor"
            )
            try:
                response = await self.gateway.route(req)
                resp_content = response.content
                if isinstance(resp_content, str):
                    cleaned = resp_content.strip()
                    if cleaned.startswith("```"):
                        cleaned = re.sub(r"^```(?:json)?\n|```$", "", cleaned, flags=re.M).strip()
                    resp_content = json.loads(cleaned)
                if isinstance(resp_content, list):
                    patched_data["leadership"] = resp_content
                    logger.info(f"✅ Patched leadership list: found {len(resp_content)} leaders.")
            except Exception as e:
                logger.warning(f"Leadership fallback extraction failed: {e}")

        # 4. Individual leader LinkedIn URLs fallback
        updated_leaders = patched_data.get("leadership") or []
        for leader in updated_leaders:
            name = leader.get("name")
            if name and not leader.get("linkedin_url"):
                query = f"{company_name} {name} LinkedIn profile"
                logger.info(f"🔍 [Fallback] Searching LinkedIn for leader '{name}': '{query}'")
                search_results = await loop.run_in_executor(None, search_duckduckgo, query)
                # Find profile link
                match = re.search(r"(https?://[a-z]{2,3}\.linkedin\.com/in/[a-zA-Z0-9_-]+)", search_results)
                if match:
                    leader["linkedin_url"] = match.group(1)
                    logger.info(f"✅ Patched leader '{name}' LinkedIn URL: {leader['linkedin_url']}")

        return patched_data

    async def extract(self, company_name: str, website_url: str) -> CompanyProfileSchema:
        """Main execution loop for dynamic website scraping, BM25 indexing, and AI gateway mapping."""
        logger.info(f"🚀 Starting dynamic extraction process for '{company_name}' at {website_url}")
        
        # 1. Scrape Homepage
        homepage_html = await self.scrape_single_page(website_url)
        homepage_clean = self.clean_html(homepage_html)
        
        # 2. Route links to buckets
        buckets = self.route_links_to_buckets(website_url, homepage_html)
        logger.info(f"🔗 Routed links: Identity={len(buckets['identity'])}, Offerings={len(buckets['offerings'])}, Corporate={len(buckets['corporate'])}")
        
        # 3. Scrape subpages concurrently
        all_scrape_targets = []
        for bucket_key in ["identity", "offerings", "corporate"]:
            all_scrape_targets.extend(buckets[bucket_key])
            
        unique_targets = list(set(all_scrape_targets))
        
        scraped_pages = [{"url": website_url, "text": homepage_clean}]
        if unique_targets:
            logger.info(f"⏳ Crawling {len(unique_targets)} unique subpages asynchronously...")
            tasks = [self.scrape_single_page(url) for url in unique_targets]
            pages_html = await asyncio.gather(*tasks, return_exceptions=True)
            for target_url, html in zip(unique_targets, pages_html):
                if isinstance(html, str) and html:
                    cleaned = self.clean_html(html)
                    if cleaned:
                        scraped_pages.append({"url": target_url, "text": cleaned})
                        
        # 4. Local BM25 query passes
        bm_cfg = self.config.get("bm25_settings", {})
        budget = bm_cfg.get("character_budget_per_pass", 4000)
        queries = bm_cfg.get("queries", {})
        
        prod_query = queries.get("product_query", "products categories features targets deployment models solutions platforms services")
        id_query = queries.get("identity_query", "founders leadership team profiles background histories executive officers")
        corp_query = queries.get("corporate_query", "legal name registered office address founding year established headquarters location city state country")
        
        logger.info("🎯 Executing 3-pass BM25 context isolation...")
        product_context = self.extract_bm25_chunks(
            scraped_pages,
            prod_query,
            budget
        )
        identity_context = self.extract_bm25_chunks(
            scraped_pages,
            id_query,
            budget
        )
        corporate_context = self.extract_bm25_chunks(
            scraped_pages,
            corp_query,
            budget
        )
        
        # 5. Phase A: Populate schemas via AIGateway calls
        logger.info("🧠 Executing Phase A AIGateway parsing runs...")
        
        # Combine identity and corporate contexts for corporate prompt
        combined_corp_context = "\n\n".join(filter(None, [identity_context, corporate_context]))
        
        corp_data_task = self._call_ai_gateway("crawler_corporate_prompt.txt", combined_corp_context, company_name)
        product_data_task = self._call_ai_gateway("crawler_product_extraction.txt", product_context, company_name)
        
        corporate_data, products_res = await asyncio.gather(corp_data_task, product_data_task)
        products_data = products_res.get("list_data") if isinstance(products_res, dict) and "list_data" in products_res else products_res
        if not isinstance(products_data, list):
            products_data = []
            
        # Construct raw profile structure
        raw_profile = {
            "company_name": company_name,
            "legal_name": corporate_data.get("legal_name"),
            "aliases": corporate_data.get("aliases") or [],
            "website_url": website_url,
            "company_linkedin_url": corporate_data.get("company_linkedin_url"),
            "founding_year": corporate_data.get("founding_year"),
            "one_liner": corporate_data.get("one_liner"),
            "description": corporate_data.get("description"),
            "business_model": corporate_data.get("business_model"),
            "target_audience": corporate_data.get("target_audience"),
            "industry": corporate_data.get("industry"),
            "sector": corporate_data.get("sector"),
            "subsector": corporate_data.get("subsector"),
            "tags": corporate_data.get("tags") or [],
            "business_models": corporate_data.get("business_models") or [],
            "headquarters": corporate_data.get("headquarters") or {},
            "products_and_solutions": products_data,
            "leadership": corporate_data.get("leadership") or []
        }
        
        # 6. Precision Field-Level Fallback Strategy (Phases B, C, D)
        logger.info("🔧 Initiating Precision Field-Level Fallback strategy (Phases B/C/D)...")
        final_profile_dict = await self.execute_precision_fallbacks(raw_profile, company_name)
        
        # Normalize and clean output values
        if final_profile_dict.get("founding_year"):
            try:
                final_profile_dict["founding_year"] = int(final_profile_dict["founding_year"])
            except ValueError:
                final_profile_dict["founding_year"] = None
                
        # Validate using Pydantic
        validated_profile = CompanyProfileSchema(**final_profile_dict)
        logger.info(f"🎉 Dynamic website extraction successfully completed for '{company_name}'!")
        return validated_profile
