# Resolution Engine

# Objective

Resolve:

* canonical startup name
* official website
* official LinkedIn URL

with high confidence.

---

# Allowed Resolution Signals

## Primary Signals

* startup name similarity
* website semantic similarity
* LinkedIn semantic similarity
* article ↔ website context similarity
* website ↔ LinkedIn similarity

---

# Secondary Validation Signals

These MUST NOT be primary resolution signals:

* founders
* geography
* investors
* competitors

These may only support validation.

---

# Output

```json
{
  "canonical_startup_name": "",
  "aliases": [],
  "website_url": "",
  "linkedin_url": "",
  "confidence_scores": {}
}
```

---

# Important Rule

Do NOT trust startup name alone.

Context similarity is critical.
