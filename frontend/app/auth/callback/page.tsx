'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import type { AuthChangeEvent, Session } from '@supabase/supabase-js';

/**
 * Finishes Google OAuth. The Supabase client reads tokens from the redirect URL
 * and establishes a session, then we send the user to the dashboard.
 */
export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState('Signing in…');

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, session: Session | null) => {
      if (session && (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED')) {
        listener.subscription.unsubscribe();
        router.replace('/dashboard');
      }
    });

    (async () => {
      const { data: s0 } = await supabase.auth.getSession();
      if (s0.session) {
        listener.subscription.unsubscribe();
        router.replace('/dashboard');
        return;
      }

      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        // eslint-disable-next-line no-await-in-loop
        const { data: s } = await supabase.auth.getSession();
        if (s.session) {
          listener.subscription.unsubscribe();
          router.replace('/dashboard');
          return;
        }
        // eslint-disable-next-line no-await-in-loop, no-promise-executor-return
        await new Promise((r) => {
          setTimeout(r, 200);
        });
      }

      listener.subscription.unsubscribe();
      setMessage('Sign-in could not be completed. Please try again from the login page.');
    })().catch(() => {
      listener.subscription.unsubscribe();
      setMessage('Sign-in could not be completed. Please try again from the login page.');
    });

    return () => listener.subscription.unsubscribe();
  }, [router]);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center text-white/80">
      {message}
    </div>
  );
}
