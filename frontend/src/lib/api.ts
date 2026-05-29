import { supabase } from './supabase'

export async function fetchStartups() {
  const { data, error } = await supabase
    .from('startups')
    .select('*')
    .limit(20)

  if (error) {
    console.error(error)
    return []
  }

  return data
}