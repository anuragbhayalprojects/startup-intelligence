# Local Development & Deployment Guide

This guide provides step-by-step instructions to clone, configure, build, and run the **Startup Intelligence OS** locally.

---

## 1. System Requirements
*   **Operating System**: macOS, Linux, or Windows (WSL2 recommended).
*   **Python**: Version 3.10 or 3.11.
*   **NodeJS**: Version 18 or 20 (with `npm`).
*   **Ollama**: For running local LLM instances.
*   **Supabase Database**: A Supabase account and database instance.

---

## 2. Step-by-Step Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/anuragbhayalprojects/startup-intelligence.git
cd startup-intelligence
```

### Step 2: Configure Environment Variables
Create a `.env` file in the project root:
```env
# Supabase Database Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-service-role-key

# Ollama Engine Setup
OLLAMA_HOST=http://localhost:11434

# Cloud Fallback (Optional)
OPENROUTER_API_KEY=your-openrouter-key
```

### Step 3: Run Database Migrations
Go to your **Supabase dashboard SQL Editor** and run the migration scripts located in `database/migrations/` in order:
1.  Run `001_initial_tables.sql` to initialize database structures.
2.  Run `009_create_news_articles.sql` to create news feeds tables and enable public RLS policies.

---

### Step 4: Python Backend Setup
Create a virtual environment, activate it, and install backend dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 5: Install Headless Playwright Browsers
Install the headless Chromium browser package for web scraping fallback features:
```bash
playwright install chromium
```

---

### Step 6: Install Local Model via Ollama
Ensure Ollama is running, then pull the target model model:
```bash
ollama run qwen2.5:3b
```

### Step 7: Node Frontend Setup
Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

---

## 3. Launching the Services

You can start both backend and frontend servers using the start script in the root directory:
```bash
chmod +x run.sh
./run.sh
```

Alternatively, you can launch them in separate terminal sessions:

### Start Backend FastAPI
```bash
source venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Start Frontend React Client
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 4. Verification & Testing

### Verification Checklist
1.  **Check API Health**: Open `http://localhost:8000/docs` in your browser to verify the Swagger API interface.
2.  **Verify Ollama Connectivity**: Run the command:
    ```bash
    curl http://localhost:11434/api/tags
    ```
    Confirm that `qwen2.5:3b` is listed in the tags payload.
3.  **Run Pipeline Tests**: Check core workflows using the test suite:
    ```bash
    pytest backend/tests/
    ```

---

## 5. Troubleshooting & FAQ

### 1. `EAGAIN` / Playwright Sandbox Errors (macOS)
*   **Symptom**: Scraper crashes during Playwright headless execution loop.
*   **Fix**: Check running processes (`ps aux | grep chrome`). Kill orphaned chrome processes or restart your machine to clear resource allocations.

### 2. Supabase HTTP/2 Protocol Issues
*   **Symptom**: Backend requests to Supabase fail or hang.
*   **Fix**: The client uses the Standard httpx connector. Ensure your environment variables do not override proxy parameters (`http_proxy`, `https_proxy`) which can disrupt connection loops.
