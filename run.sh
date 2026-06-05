#!/bin/bash

# Terminate background processes on exit
cleanup() {
  echo ""
  echo "Shutting down servers..."
  if [ ! -z "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
  fi
  if [ ! -z "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null
  fi
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "========================================================="
echo "  Starting ICICI Startup Intelligence Stack..."
echo "========================================================="

# 1. Start backend (FastAPI)
echo "🚀 Launching FastAPI Backend on port 8000..."
if [ -d "venv" ]; then
  source venv/bin/activate
  uvicorn backend.api.main:app --port 8000 --reload &
else
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  uvicorn backend.api.main:app --port 8000 --reload &
fi
BACKEND_PID=$!

# 2. Start frontend (Vite React)
echo "🚀 Launching Vite React Frontend on port 5173..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo "========================================================="
echo "  ICICI Startup Intelligence Stack is now running!"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend:  http://localhost:8000"
echo "  Press Ctrl+C to terminate both servers."
echo "========================================================="

# Wait for background jobs to finish
wait
