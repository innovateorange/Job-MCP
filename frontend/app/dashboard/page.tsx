'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function Dashboard() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session) {
        router.push('/login');
        return;
      }
      
      setUser(session.user);
      setLoading(false);
    };

    checkUser();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.push('/login');
      } else {
        setUser(session.user);
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  if (loading) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white pt-24 px-6">
      <div className="max-w-7xl mx-auto">
        {/* Welcome Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Dashboard</h1>
          <p className="text-white/60">Welcome back, {user?.email}</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Card 1 */}
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">Applications</div>
            <div className="text-3xl font-bold mb-1">0</div>
            <div className="text-white/40 text-xs">No applications yet</div>
          </div>

          {/* Card 2 */}
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">In Progress</div>
            <div className="text-3xl font-bold mb-1">0</div>
            <div className="text-white/40 text-xs">Active applications</div>
          </div>

          {/* Card 3 */}
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">Completed</div>
            <div className="text-3xl font-bold mb-1">0</div>
            <div className="text-white/40 text-xs">Successfully submitted</div>
          </div>
        </div>

        {/* User Info Card */}
        <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
          <h2 className="text-2xl font-semibold mb-4">Account Information</h2>
          <div className="space-y-3">
            <div>
              <div className="text-white/60 text-sm mb-1">Email</div>
              <div className="text-white">{user?.email}</div>
            </div>
            <div>
              <div className="text-white/60 text-sm mb-1">User ID</div>
              <div className="text-white/80 font-mono text-sm">{user?.id}</div>
            </div>
            <div>
              <div className="text-white/60 text-sm mb-1">Account Created</div>
              <div className="text-white">
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Coming Soon Section */}
        <div className="mt-8 backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6 text-center">
          <h3 className="text-xl font-semibold mb-2">More Features Coming Soon</h3>
          <p className="text-white/60">
            Track your job applications, manage your profile, and more!
          </p>
        </div>
      </div>
    </main>
  );
}
