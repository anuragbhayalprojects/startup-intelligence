# Company Intelligence JSONB Schema

# Final Structure

```json
{
  "basic_information": {},
  "business_profile": {},
  "founders_details": [],
  "products_services": [],
  "funding_details": {},
  "competitors": [],
  "digital_presence": {},
  "validation_metadata": {},
  "source_metadata": {}
}
```

---

# Frontend Alignment

The backend schema MUST directly mirror:
Company Intelligence UI sections.

---

# Required Features

All sections must support:

* field-level re-enrichment
* confidence scoring
* source traceability
* partial updates
* retry handling
* modular rendering

---

# Important Principle

This is a:
frontend-driven intelligence architecture

NOT a generic backend-centric graph architecture.
