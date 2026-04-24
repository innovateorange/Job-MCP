'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

function passwordChecks(password: string) {
  return [
    {
      key: 'length',
      label: 'At least 7 characters',
      met: password.length >= 7,
    },
    {
      key: 'number',
      label: 'At least 1 number (0-9)',
      met: /[0-9]/.test(password),
    },
    {
      key: 'upper',
      label: 'At least 1 uppercase letter (A-Z)',
      met: /[A-Z]/.test(password),
    },
    {
      key: 'lower',
      label: 'At least 1 lowercase letter (a-z)',
      met: /[a-z]/.test(password),
    },
    {
      key: 'special',
      label: 'At least 1 special character (e.g. ! @ # $)',
      met: /[^A-Za-z0-9]/.test(password),
    },
  ];
}

export default function SignUpPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ kind: 'text'; message: string } | null>(null);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  const checks = passwordChecks(password);
  const allPasswordChecksMet = checks.every((c) => c.met);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!allPasswordChecksMet) {
      setError({
        kind: 'text',
        message: 'Please update your password to meet all requirements shown below.',
      });
      setLoading(false);
      return;
    }

    if (!passwordsMatch) {
      setError({
        kind: 'text',
        message: 'Passwords do not match. Please confirm the same password in both fields.',
      });
      setLoading(false);
      return;
    }

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (signUpError) throw signUpError;

      if (data.user) {
        setSuccess(true);
        // Check if email confirmation is required
        if (data.user.identities && data.user.identities.length === 0) {
          setError({
            kind: 'text',
            message: 'This email is already registered. Please sign in instead.',
          });
        } else {
          // Redirect to dashboard after successful signup
          setTimeout(() => {
            router.push('/dashboard');
          }, 1500);
        }
      }
    } catch (err: any) {
      const m = err?.message ?? String(err);
      if (m === 'Failed to fetch' || err?.name === 'TypeError') {
        setError({
          kind: 'text',
          message:
            'Cannot reach Supabase. Check your network, and that this site’s deployment has NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY set in Vercel.',
        });
      } else {
        setError({ kind: 'text', message: m || 'An error occurred during sign up' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignUp = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const { error: signUpError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (signUpError) throw signUpError;
    } catch (err: any) {
      const m = err?.message ?? String(err);
      if (m === 'Failed to fetch' || err?.name === 'TypeError') {
        setError({
          kind: 'text',
          message:
            'Cannot reach Supabase. Check your network, and that this site’s deployment has NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY set in Vercel.',
        });
      } else {
        let errorMessage = 'Failed to sign up with Google';
        if (m.includes('provider is not enabled') || err.code === 'validation_failed') {
          errorMessage = 'Google sign-in is not enabled. Please enable it in your Supabase dashboard under Authentication > Providers.';
        } else if (m) {
          errorMessage = m;
        }
        setError({ kind: 'text', message: errorMessage });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-6">
      <div className="max-w-md w-full">
        {/* Liquid Glass Card */}
        <div className="relative">
          {/* Glow effect */}
          <div className="absolute inset-0 bg-white/5 blur-3xl rounded-3xl" />
          
          {/* Main card */}
          <div className="relative backdrop-blur-xl bg-white/5 border border-white/10 rounded-3xl p-8 md:p-10">
            <h1 className="text-3xl font-semibold text-white mb-2">Create Account</h1>
            <p className="text-white/60 mb-8">Get started with Job-MCP</p>

            {error?.kind === 'text' && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {error.message}
              </div>
            )}

            {success && (
              <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm">
                Account created successfully! Redirecting to dashboard...
              </div>
            )}

            <form onSubmit={handleSignUp} className="space-y-6">
              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-white/80 mb-2">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all"
                  placeholder="you@example.com"
                />
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-white/80 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={7}
                    autoComplete="new-password"
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all pr-24"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 text-xs font-semibold rounded-lg bg-white/5 border border-white/10 text-white/80 hover:bg-white/10 transition-colors disabled:opacity-50"
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>

                <div className="mt-3">
                  <div className="text-xs font-medium text-white/70 mb-2">Password requirements</div>
                  <div className="space-y-1">
                    {checks.map((c) => (
                      <label key={c.key} className="flex items-start gap-2 cursor-default select-none">
                        <input type="checkbox" checked={c.met} readOnly className="mt-0.5" />
                        <span className={c.met ? 'line-through text-white/50' : 'text-white/70'}>{c.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-white/80 mb-2">
                  Confirm password
                </label>
                <div className="relative">
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all pr-24"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1 text-xs font-semibold rounded-lg bg-white/5 border border-white/10 text-white/80 hover:bg-white/10 transition-colors disabled:opacity-50"
                  >
                    {showConfirmPassword ? 'Hide' : 'Show'}
                  </button>
                </div>

                {confirmPassword.length > 0 && !passwordsMatch && (
                  <div className="mt-2 text-xs text-red-400">Passwords don&apos;t match.</div>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full px-6 py-3.5 bg-white text-black rounded-xl font-semibold hover:bg-white/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Creating account...' : 'Sign Up'}
              </button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-transparent text-white/60">Or continue with</span>
              </div>
            </div>

            {/* Google Sign Up Button */}
            <button
              type="button"
              onClick={handleGoogleSignUp}
              disabled={loading}
              className="w-full px-6 py-3.5 bg-white/5 border border-white/10 rounded-xl font-semibold text-white hover:bg-white/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              {loading ? 'Signing up...' : 'Sign up with Google'}
            </button>

            {/* Sign In Link */}
            <p className="mt-6 text-center text-sm text-white/60">
              Already have an account?{' '}
              <Link href="/login" className="text-white hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

