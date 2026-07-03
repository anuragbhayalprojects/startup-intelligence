# Source Collection & Cleaning

# Objective

Collect, preserve, segment, and clean all meaningful startup intelligence sources.

---

# Raw Source Collection

Collect raw content from:

* homepage
* about us
* products/services
* founders/team
* contact us
* footer
* LinkedIn homepage
* LinkedIn about page
* search snippets

---

# Important Rule

DO NOT blindly remove footer content.

Critical metadata often exists in:

* footer
* contact pages
* social links

---

# Raw Source Payload Structure

```json
{
  "homepage_html": "",
  "about_page_html": "",
  "products_page_html": "",
  "team_page_html": "",
  "contact_page_html": "",
  "footer_html": "",
  "linkedin_pages": {},
  "search_snippets": []
}
```

---

# Cleaning & Segmentation

Segment into:

* homepage
* about_page
* products_services
* founders_team
* funding_investors
* contact_us
* social_presence
* compliance_legal
* careers
* seo_metadata
* raw_text_chunks

---

# Cleaning Goals

* preserve semantic meaning
* preserve metadata
* remove noise
* normalize formatting
* reduce token size
* improve downstream enrichment quality

---

# Important Principle

This should become:
SOURCE-CENTRIC ARCHITECTURE

NOT:
SCRAPER-CENTRIC ARCHITECTURE
