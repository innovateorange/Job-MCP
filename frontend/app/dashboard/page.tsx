'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { getApiBaseUrl } from '@/lib/api';
import type { AuthChangeEvent, Session } from '@supabase/supabase-js';

type DashboardJob = {
  id: string;
  company: string;
  title: string;
  location: string;
  source: string;
  autoAppliedAt: string;
  requiresFollowUp: boolean;
  followUpConfirmed: boolean;
  status: 'auto_applied' | 'follow_up_required' | 'completed';
};

export default function Dashboard() {
  const [user, setUser] = useState<{ id: string; email?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState('');
  const [jobs, setJobs] = useState<DashboardJob[]>([]);
  const router = useRouter();

  const stats = useMemo(() => {
    const total = jobs.length;
    const autoApplied = jobs.filter((job) => job.status === 'auto_applied').length;
    const followUpRequired = jobs.filter((job) => job.requiresFollowUp && !job.followUpConfirmed).length;
    const completed = jobs.filter((job) => job.status === 'completed' || job.followUpConfirmed).length;
    return { total, autoApplied, followUpRequired, completed };
  }, [jobs]);

  const fetchJobs = useCallback(async (userId: string) => {
    setJobsLoading(true);
    setJobsError('');

    try {
      const res = await fetch(`${getApiBaseUrl()}/apply/jobs/${userId}`);
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const d = (data as { detail?: unknown })?.detail;
        const msg =
          typeof d === 'string'
            ? d
            : res.statusText || 'Failed to load application data from the API.';
        setJobsError(msg);
        setJobs([]);
        return;
      }

      const rows = (data as { rows?: unknown[] }).rows ?? [];
      const mapped: DashboardJob[] = (rows as any[]).map((row) => ({
        id: String(row.id),
        company: row.company ?? 'Unknown Company',
        title: row.title ?? 'Untitled Role',
        location: row.location ?? 'N/A',
        source: row.source ?? 'Job Board',
        autoAppliedAt: row.auto_applied_at ?? new Date().toISOString(),
        requiresFollowUp: Boolean(row.requires_follow_up),
        followUpConfirmed: Boolean(row.follow_up_confirmed),
        status:
          row.status === 'completed' || row.status === 'follow_up_required' || row.status === 'auto_applied'
            ? row.status
            : 'auto_applied',
      }));

      setJobs(mapped);
    } catch (e) {
      setJobsError(e instanceof Error ? e.message : 'Network error while loading jobs.');
      setJobs([]);
    } finally {
      setJobsLoading(false);
    }
  }, []);

  const handleFollowUpToggle = async (jobId: string, wasConfirmed: boolean) => {
    const followUpConfirmed = !wasConfirmed;
    setJobsError('');

    try {
      const res = await fetch(`${getApiBaseUrl()}/apply/jobs/${jobId}/follow-up`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ follow_up_confirmed: followUpConfirmed }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const d = (data as { detail?: unknown })?.detail;
        setJobsError(typeof d === 'string' ? d : `Update failed (${res.status})`);
        return;
      }

      if (user?.id) {
        await fetchJobs(user.id);
      }
    } catch (e) {
      setJobsError(e instanceof Error ? e.message : 'Network error');
    }
  };

  const formatDateTime = (input: string) => {
    const date = new Date(input);
    return Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleString();
  };

  const renderStatus = (job: DashboardJob) => {
    if (job.followUpConfirmed || job.status === 'completed') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs bg-emerald-400/20 text-emerald-300 border border-emerald-300/20">
          Completed
        </span>
      );
    }

    if (job.requiresFollowUp || job.status === 'follow_up_required') {
      return (
        <span className="px-2.5 py-1 rounded-full text-xs bg-amber-300/20 text-amber-200 border border-amber-300/20">
          Needs Follow-Up
        </span>
      );
    }

    return (
      <span className="px-2.5 py-1 rounded-full text-xs bg-sky-400/20 text-sky-300 border border-sky-300/20">
        Auto-Applied
      </span>
    );
  };

  useEffect(() => {
    const checkUser = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push('/login');
        return;
      }

      setUser({ id: session.user.id, email: session.user.email });
      await fetchJobs(session.user.id);
      setLoading(false);
    };

    checkUser();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event: AuthChangeEvent, session: Session | null) => {
      if (!session) {
        router.push('/login');
      } else {
        setUser({ id: session.user.id, email: session.user.email });
        fetchJobs(session.user.id);
      }
    });

    return () => subscription.unsubscribe();
  }, [router, fetchJobs]);

  if (loading) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white pt-24 px-4 md:px-6 pb-10">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-4xl font-bold mb-2">Application Grid</h1>
          <p className="text-white/60">
            Auto-applied jobs and follow-ups in one spreadsheet view for {user?.email}
          </p>
          <p className="text-white/40 text-sm mt-2">
            Data source: <code className="text-white/60">{getApiBaseUrl()}/apply/jobs/&lt;user_id&gt;</code>
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">Total Rows</div>
            <div className="text-3xl font-bold mb-1">{stats.total}</div>
            <div className="text-white/40 text-xs">All tracked applications</div>
          </div>
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">Auto-Applied</div>
            <div className="text-3xl font-bold mb-1">{stats.autoApplied}</div>
            <div className="text-white/40 text-xs">No action needed yet</div>
          </div>
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">Needs Follow-Up</div>
            <div className="text-3xl font-bold mb-1">{stats.followUpRequired}</div>
            <div className="text-white/40 text-xs">Pending manual completion</div>
          </div>
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <div className="text-white/60 text-sm mb-2">Completed</div>
            <div className="text-3xl font-bold mb-1">{stats.completed}</div>
            <div className="text-white/40 text-xs">Follow-up confirmed</div>
          </div>
        </div>

        {jobsError && (
          <div className="mb-4 p-3 rounded-lg border border-amber-300/30 bg-amber-300/10 text-amber-100 text-sm">
            {jobsError}
          </div>
        )}

        <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
          <div className="px-5 py-4 border-b border-white/10 text-sm text-white/70">
            Spreadsheet view. Jobs that require extra action are flagged, and you can manually confirm when follow-up is
            complete (updates via PATCH on the API).
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead className="bg-white/5 text-white/70">
                <tr>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Company</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Role</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Location</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Source</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Auto Applied At</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Status</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Requires Follow-Up</th>
                  <th className="text-left font-medium px-4 py-3 border-b border-white/10">Follow-Up Confirmed</th>
                </tr>
              </thead>
              <tbody>
                {jobsLoading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-white/60">
                      Loading spreadsheet rows...
                    </td>
                  </tr>
                ) : jobs.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-white/60">
                      No jobs yet. Start from{' '}
                      <Link href="/apply" className="text-sky-300 underline">
                        Auto-apply
                      </Link>{' '}
                      or wait for the worker to record applications in the database.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-white/[0.03] transition-colors">
                      <td className="px-4 py-3 border-b border-white/5">{job.company}</td>
                      <td className="px-4 py-3 border-b border-white/5">{job.title}</td>
                      <td className="px-4 py-3 border-b border-white/5 text-white/75">{job.location}</td>
                      <td className="px-4 py-3 border-b border-white/5 text-white/75">{job.source}</td>
                      <td className="px-4 py-3 border-b border-white/5 text-white/75 whitespace-nowrap">
                        {formatDateTime(job.autoAppliedAt)}
                      </td>
                      <td className="px-4 py-3 border-b border-white/5">{renderStatus(job)}</td>
                      <td className="px-4 py-3 border-b border-white/5">
                        <span className={job.requiresFollowUp ? 'text-amber-200' : 'text-white/45'}>
                          {job.requiresFollowUp ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="px-4 py-3 border-b border-white/5">
                        <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={job.followUpConfirmed}
                            onChange={() => handleFollowUpToggle(job.id, job.followUpConfirmed)}
                            className="h-4 w-4 rounded border-white/30 bg-transparent"
                          />
                          <span className="text-white/80">Confirmed</span>
                        </label>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  );
}
