'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import { getApiBaseUrl } from '@/lib/api';

type TaskStatusPayload = {
  task_id: string;
  status: string;
  result?: unknown;
};

function parseUrls(raw: string): string[] {
  return raw
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export default function ApplyPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [jobUrlText, setJobUrlText] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [taskIds, setTaskIds] = useState<string[]>([]);
  const [statusByTask, setStatusByTask] = useState<Record<string, TaskStatusPayload>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const fetchStatus = useCallback(async (ids: string[]) => {
    const next: Record<string, TaskStatusPayload> = {};
    for (const id of ids) {
      try {
        const res = await fetch(`${getApiBaseUrl()}/apply/status/${id}`);
        const data = (await res.json()) as TaskStatusPayload;
        if (res.ok) {
          next[id] = data;
        } else {
          next[id] = { task_id: id, status: 'ERROR', result: data };
        }
      } catch (e) {
        next[id] = {
          task_id: id,
          status: 'ERROR',
          result: e instanceof Error ? e.message : 'fetch failed',
        };
      }
    }
    setStatusByTask((prev) => ({ ...prev, ...next }));

    const allTerminal = ids.every((id) => {
      const s = next[id]?.status;
      return s === 'SUCCESS' || s === 'FAILURE' || s === 'REVOKED' || s === 'ERROR';
    });
    if (allTerminal) {
      stopPolling();
    }
  }, [stopPolling]);

  useEffect(() => {
    const run = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }
      setUserId(session.user.id);
      setEmail((e) => e || session.user.email || '');
      setLoading(false);
    };
    run();
  }, [router]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const handleStart = async () => {
    setError('');
    setInfo('');
    const urls = parseUrls(jobUrlText);
    if (!userId || urls.length === 0) {
      setError('Sign in and enter at least one job URL.');
      return;
    }

    setStarting(true);
    stopPolling();

    try {
      const res = await fetch(`${getApiBaseUrl()}/apply/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          job_urls: urls,
          credentials: { email: email.trim(), password },
          preferences: {},
        }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const d = (data as { detail?: unknown })?.detail;
        setError(typeof d === 'string' ? d : `Start failed (${res.status})`);
        setStarting(false);
        return;
      }

      const taskIdRaw = (data as { task_id?: string }).task_id || '';
      const ids = taskIdRaw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      setTaskIds(ids);
      setInfo(`Queued ${(data as { jobs_queued?: number }).jobs_queued ?? ids.length} application task(s). Polling status…`);

      await fetchStatus(ids);

      pollRef.current = setInterval(() => {
        void fetchStatus(ids);
      }, 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error — is the API and Celery worker running?');
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center">
        Loading…
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white pt-24 px-6 pb-16">
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Auto-apply</h1>
          <p className="text-white/60 text-sm">
            POST to <code className="text-white/80">{getApiBaseUrl()}/apply/start</code> and poll{' '}
            <code className="text-white/80">/apply/status/{"{task_id}"}</code>. Requires a running API and Celery worker
            with Redis.
          </p>
        </div>

        {error && <div className="p-3 rounded-lg border border-red-400/30 bg-red-500/10 text-red-200 text-sm">{error}</div>}
        {info && <div className="p-3 rounded-lg border border-sky-400/30 bg-sky-500/10 text-sky-100 text-sm">{info}</div>}

        <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6 space-y-5">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-white/80">Job URLs (one per line)</label>
            <textarea
              value={jobUrlText}
              onChange={(e) => setJobUrlText(e.target.value)}
              rows={5}
              placeholder="https://boards.greenhouse.io/..."
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/35 focus:outline-none focus:border-white/30"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-white/80">Portal email (optional)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white"
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-white/80">Portal password (optional)</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white"
                autoComplete="current-password"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={() => void handleStart()}
            disabled={starting}
            className="px-5 py-2.5 rounded-xl bg-white text-black font-semibold hover:bg-white/90 disabled:opacity-50"
          >
            {starting ? 'Starting…' : 'Queue applications'}
          </button>
        </div>

        {taskIds.length > 0 && (
          <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-4">Task status</h2>
            <ul className="space-y-3 text-sm">
              {taskIds.map((id) => {
                const st = statusByTask[id];
                return (
                  <li key={id} className="border border-white/10 rounded-lg p-3 bg-black/20">
                    <div className="text-white/50 text-xs break-all mb-1">{id}</div>
                    <div className="text-white/90">
                      Status: <span className="text-amber-200">{st?.status ?? '…'}</span>
                    </div>
                    {st?.result != null && (
                      <pre className="text-xs text-white/50 mt-2 overflow-x-auto max-h-32">
                        {JSON.stringify(st.result, null, 2)}
                      </pre>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <p className="text-white/45 text-sm">
          Track outcomes on the{' '}
          <Link href="/dashboard" className="text-sky-300 underline">
            dashboard
          </Link>{' '}
          once rows are written to your backend database.
        </p>
      </div>
    </main>
  );
}
