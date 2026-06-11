import axios from "axios";
import API from "../services/api";

const generateFrontendTraceId = (): string => {
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const randomStr = Math.random().toString(36).substring(2, 8).toUpperCase();
  return `TRACE_${dateStr}_${randomStr}`;
};

// Initialize or get the current trace ID
if (!sessionStorage.getItem("current_trace_id")) {
  sessionStorage.setItem("current_trace_id", generateFrontendTraceId());
}

export const getActiveTraceId = (): string => {
  return sessionStorage.getItem("current_trace_id") || generateFrontendTraceId();
};

export const rotateTraceId = (): string => {
  const newId = generateFrontendTraceId();
  sessionStorage.setItem("current_trace_id", newId);
  return newId;
};

// Intercept window.fetch globally
const originalFetch = window.fetch;
window.fetch = async function (input, init) {
  const traceId = getActiveTraceId();
  const inputStr = typeof input === "string" ? input : (input instanceof Request ? input.url : "");
  
  const isApiCall = inputStr.includes("/api") || 
                    inputStr.includes("localhost:8000") || 
                    inputStr.includes("up.railway.app");
                    
  if (isApiCall) {
    init = init || {};
    if (!init.headers) {
      init.headers = {};
    }
    
    if (init.headers instanceof Headers) {
      init.headers.set("X-Trace-ID", traceId);
    } else if (Array.isArray(init.headers)) {
      const hasHeader = init.headers.some(([k]) => k.toLowerCase() === "x-trace-id");
      if (!hasHeader) {
        init.headers.push(["X-Trace-ID", traceId]);
      }
    } else {
      init.headers = {
        ...init.headers,
        "X-Trace-ID": traceId
      };
    }
  }
  
  return originalFetch.call(this, input, init);
};

// Intercept Axios requests
API.interceptors.request.use((config) => {
  config.headers = config.headers || {};
  config.headers["X-Trace-ID"] = getActiveTraceId();
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Logs a frontend event to the backend
export const logFrontendEvent = async (page: string, component: string, action: string, payload: any = {}) => {
  const traceId = getActiveTraceId();
  const rawApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
  const apiBase = rawApiUrl.endsWith("/") 
    ? (rawApiUrl.endsWith("/api/") ? rawApiUrl.slice(0, -1) : rawApiUrl + "api") 
    : (rawApiUrl.endsWith("/api") ? rawApiUrl : rawApiUrl + "/api");
    
  try {
    await originalFetch(`${apiBase}/observability/event`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Trace-ID": traceId
      },
      body: JSON.stringify({ page, component, action, payload })
    });
  } catch (e) {
    console.warn("Failed to log frontend event:", e);
  }
};
