'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import LiquidGlassButton from './LiquidGlassButton';

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  // Set to false to show Sign In/Sign Up buttons (mockup mode)
  // Set to true to show Dashboard button
  const isSignedIn = false;

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-black/95 backdrop-blur-md border-b border-white/10'
          : 'bg-black'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 hover:opacity-80 transition-opacity">
            <div className="text-xl font-semibold text-white">
              Job-MCP
            </div>
          </Link>

          {/* Center Navigation */}
          <div className="hidden md:flex items-center space-x-8">
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
              // Signed In: Show Dashboard
              <Link
                href="/dashboard"
                className="flex items-center space-x-2 text-sm font-medium text-white hover:opacity-80 transition-opacity"
              >
                <span>Dashboard</span>
                <span className="px-1.5 py-0.5 text-xs font-medium bg-white/10 text-white rounded border border-white/20">
                  D
                </span>
              </Link>
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

