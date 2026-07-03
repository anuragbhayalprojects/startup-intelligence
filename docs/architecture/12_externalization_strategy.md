# Externalization Strategy

# Objective

Reduce hardcoded logic and make the architecture configuration-driven.

---

# Externalize

## AI Layer

* prompts
* model configs
* routing priorities
* retry rules
* timeout rules
* fallback rules

---

## Search Layer

* search templates
* query expansions
* coverage rules
* ranking rules

---

## Resolution Layer

* confidence thresholds
* similarity weights
* scoring rules
* validation rules

---

## Enrichment Layer

* enrichment schemas
* field mappings
* extraction rules
* section priorities

---

# Config Files

```text
configs/
├── search_templates.json
├── model_routing.json
├── enrichment_modules.json
├── confidence_rules.json
├── retry_policies.json
└── pipeline_config.json
```

---

# Important Rule

Avoid:

* hardcoded prompts
* hardcoded model names
* hardcoded thresholds
* hardcoded retry counts

Prefer:
config-driven orchestration
