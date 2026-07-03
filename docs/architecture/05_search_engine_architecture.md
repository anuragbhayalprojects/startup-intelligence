# Search Engine Architecture

# Core Principle

Use:

* dynamic query generation
* query permutations
* fallback templates

NOT static-only templates.

---

# Search Flow

STARTUP NAME
↓
Dynamic Query Generation
↓
Permutation Expansion
↓
Search Execution
↓
Coverage Detection
↓
Fallback → search_templates.json

---

# Search Types

## Identity

* official website
* LinkedIn
* legal entity

## Founders

* founders
* CEO
* leadership

## Funding

* funding
* investors
* Series A
* valuation

## Products

* products
* solutions
* platform

---

# Important Rule

search_templates.json acts as:
fallback recovery mechanism

NOT primary search engine.

---

# Example Dynamic Queries

```text
{startup} official website
{startup} LinkedIn
{startup} founders
{startup} funding
{startup} investors
{startup} products
```
