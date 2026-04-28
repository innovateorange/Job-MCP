import { createClient as createSupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const missingEnvError =
  'Missing Supabase environment variables. Please create a .env.local file in the frontend directory with:\n' +
  'NEXT_PUBLIC_SUPABASE_URL=your_supabase_url\n' +
  'NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key\n\n' +
  'Get these values from your Supabase project settings: https://app.supabase.com/project/_/settings/api';

function createThrowingSupabaseClient() {
  return new Proxy(
    {},
    {
      get() {
        throw new Error(missingEnvError);
      },
    }
  );
}

export const supabase =
  supabaseUrl && supabaseKey ? createSupabaseClient(supabaseUrl, supabaseKey) : (createThrowingSupabaseClient() as any);

// Client-side function to create Supabase client
export const createClient = () => {
  if (!supabaseUrl || !supabaseKey) {
    throw new Error(missingEnvError);
  }
  return createSupabaseClient(supabaseUrl, supabaseKey);
};
