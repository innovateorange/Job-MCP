import { createClient as createSupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    'Supabase configuration missing. Make sure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set.',
  );
}

export const supabase = createSupabaseClient(supabaseUrl, supabaseKey);

// Client-side function to create Supabase client
export const createClient = () => {
  return createSupabaseClient(supabaseUrl, supabaseKey);
};
