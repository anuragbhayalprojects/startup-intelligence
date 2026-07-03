# Code Quality Rules

# Mandatory Requirements

1. Modular architecture
2. Typed schemas/interfaces
3. Reusable services
4. Shared utilities
5. Config-driven behavior
6. Minimal duplication
7. Proper logging
8. Failure isolation
9. Retry handling
10. Strong observability

---

# Folder Structure Goals

Prefer:

* modular services
* isolated AI layers
* shared utilities
* reusable processors
* centralized configs

Avoid:

* giant service files
* deeply coupled modules
* duplicated enrichment logic

---

# AI Layer Rules

Avoid:

* excessive AI calls
* autonomous agent loops
* uncontrolled retries

Prefer:

* structured extraction
* deterministic pipelines
* bounded retries
* modular enrichers

---

# Database Rules

Prefer:

* JSONB modularity
* partial updates
* schema flexibility

Avoid:

* over-normalization
* excessive joins
* unnecessary tables

---

# Frontend Rules

Backend output must:
directly map to frontend rendering structure.
