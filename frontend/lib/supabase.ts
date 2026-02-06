import { createClient as createSupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    'Missing Supabase environment variables. Please create a .env.local file in the frontend directory with:\n' +
    'NEXT_PUBLIC_SUPABASE_URL=your_supabase_url\n' +
    'NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key\n\n' +
    'Get these values from your Supabase project settings: https://app.supabase.com/project/_/settings/api'
  );
}

export const supabase = createSupabaseClient(supabaseUrl, supabaseKey);

// Client-side function to create Supabase client
export const createClient = () => {
  return createSupabaseClient(supabaseUrl, supabaseKey);
};
