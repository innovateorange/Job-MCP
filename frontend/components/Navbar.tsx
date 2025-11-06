'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import LiquidGlassButton from './LiquidGlassButton';
import { supabase } from '@/lib/supabase';

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const router = useRouter();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    // Check initial auth state
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsSignedIn(!!session);
      setUserEmail(session?.user?.email || '');
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsSignedIn(!!session);
      setUserEmail(session?.user?.email || '');
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-black/95 backdrop-blur-md border-b border-white/10'
          : 'bg-black'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16 relative">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 hover:opacity-80 transition-opacity">
            <div className="text-xl font-semibold text-white">
              Job-MCP
            </div>
          </Link>

          {/* Center Navigation - Absolutely positioned to center of screen */}
          <div className="hidden md:flex items-center space-x-8 absolute left-1/2 -translate-x-1/2">
            <Link
              href="/features"
              className="text-sm font-medium text-white/70 hover:text-white transition-colors"
            >
              Features
            </Link>
            <Link
              href="/resources"
              className="text-sm font-medium text-white/70 hover:text-white transition-colors"
            >
              Resources
            </Link>
          </div>

          {/* Right Actions */}
          <div className="flex items-center space-x-4">
            {isSignedIn ? (
              // Signed In: Show Dashboard and Sign Out
              <>
                <Link
                  href="/dashboard"
                  className="flex items-center space-x-2 text-sm font-medium text-white hover:opacity-80 transition-opacity"
                >
                  <span className="hidden md:inline">Dashboard</span>
                  <span className="px-2 py-1 text-xs font-medium bg-white/10 text-white rounded border border-white/20">
                    {userEmail.charAt(0).toUpperCase()}
                  </span>
                </Link>
                <button
                  onClick={handleSignOut}
                  className="text-sm font-medium text-white/70 hover:text-white transition-colors"
                >
                  Sign Out
                </button>
              </>
            ) : (
              // Not Signed In: Show Sign In / Sign Up with Liquid Glass
              <>
                <Link
                  href="/login"
                  className="hidden sm:block text-sm font-medium text-white/70 hover:text-white transition-colors"
                >
                  Sign In
                </Link>
                <LiquidGlassButton href="/signup">
                  Sign Up
                </LiquidGlassButton>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

