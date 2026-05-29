import { supabase } from "./supabase";

export async function fetchStartups() {
  const { data, error } = await supabase
    .from("startups")
    .select("*")
    .limit(20);

  if (error) {
    console.error("Supabase error:", error);
    return [];
  }

  // ✅ CRITICAL SAFETY FIX
  if (!Array.isArray(data)) {
    console.warn("Unexpected Supabase response:", data);
    return [];
  }

  return data;
}