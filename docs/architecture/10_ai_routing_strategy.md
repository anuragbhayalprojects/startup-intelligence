# AI Routing Strategy

# Primary Provider

OpenRouter API

---

# Fallback Strategy

Fallback to local AI models if:

* API unavailable
* timeout
* rate limit
* missing API key
* budget threshold exceeded

---

# Suggested Local Models

* Qwen
* Llama

---

# Important Rule

Local models are fallback systems.

NOT primary orchestration systems.

---

# Externalize

Externalize:

* model configs
* routing priorities
* retry configs
* timeout rules
* fallback rules
* cost thresholds

---

# Modular AI Layer Design

## AI Layer #1

Startup extraction

## AI Layer #2

Resolution

## AI Layer #3

Modular enrichment
