'use client';

import Link from 'next/link';

interface LiquidGlassButtonProps {
  href: string;
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
}

export default function LiquidGlassButton({ href, children, variant = 'primary' }: LiquidGlassButtonProps) {
  return (
    <Link href={href}>
      <div className="relative group cursor-pointer">
        {/* Liquid Glass Effect */}
        <div
          className={`
            relative px-6 py-2.5 rounded-full
            backdrop-blur-2xl
            border border-white/10
            transition-all duration-300
            group-hover:scale-105
            group-hover:border-white/20
            ${
              variant === 'primary'
                ? 'bg-white/5 hover:bg-white/8'
                : 'bg-white/3 hover:bg-white/5'
            }
          `}
        >
          {/* Frosted overlay */}
          <div
            className="absolute inset-0 rounded-full bg-gradient-to-br from-white/10 via-white/3 to-transparent opacity-40 group-hover:opacity-60 transition-opacity duration-300"
          />
          
          {/* Glow effect on hover */}
          <div
            className="absolute inset-0 rounded-full bg-white/0 group-hover:bg-white/5 blur-xl transition-all duration-500"
          />
          
          {/* Content */}
          <span className="relative z-10 text-sm font-medium text-white drop-shadow-lg">
            {children}
          </span>
        </div>

        {/* Animated border gradient */}
        <div
          className="absolute inset-0 rounded-full bg-gradient-to-r from-white/0 via-white/10 to-white/0 opacity-0 group-hover:opacity-100 blur-sm transition-opacity duration-500 -z-10"
        />
      </div>
    </Link>
  );
}

