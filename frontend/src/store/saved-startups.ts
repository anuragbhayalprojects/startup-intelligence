import { useEffect, useState } from "react";

const KEY = "icici-sios-saved";

function read(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    return new Set(JSON.parse(localStorage.getItem(KEY) ?? "[]"));
  } catch {
    return new Set();
  }
}

const listeners = new Set<() => void>();
let cache: Set<string> | null = null;

function getSet() {
  if (cache === null) cache = read();
  return cache;
}

function persist() {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(Array.from(getSet())));
  listeners.forEach((l) => l());
}

export function toggleSaved(id: string) {
  const s = getSet();
  if (s.has(id)) s.delete(id);
  else s.add(id);
  persist();
}

export function useSavedStartups() {
  const [, force] = useState(0);
  useEffect(() => {
    const l = () => force((n) => n + 1);
    listeners.add(l);
    // refresh from localStorage on mount (SSR)
    cache = read();
    force((n) => n + 1);
    return () => {
      listeners.delete(l);
    };
  }, []);
  return {
    saved: getSet(),
    toggle: toggleSaved,
    isSaved: (id: string) => getSet().has(id),
  };
}
