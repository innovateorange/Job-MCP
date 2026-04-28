'use client';

import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { getApiBaseUrl } from '@/lib/api';

export type ParseResumeResponse = {
  file_name?: string;
  profile?: Record<string, unknown>;
  skills?: { skills?: string[]; categorized?: Record<string, unknown> };
  contact_info?: { email?: string; phone?: string } | null;
  processing_status?: string;
  error?: string;
};

type ParseState = 'idle' | 'uploading' | 'saving' | 'success' | 'error';

function buildExperiencePayload(
  data: ParseResumeResponse
): { text: string; parsed: unknown; contact_info: unknown; parsed_at: string } {
  const profile = (data.profile || {}) as {
    summary?: string;
    experience?: Array<{ company?: string; title?: string; description?: string }>;
    education?: Array<{ degree?: string; institution?: string }>;
  };
  const lines: string[] = [];
  if (profile.summary) lines.push(profile.summary);
  if (Array.isArray(profile.experience)) {
    for (const ex of profile.experience) {
      const t = [ex.title, ex.company].filter(Boolean).join(' @ ');
      if (t) lines.push(t);
      if (ex.description) lines.push(ex.description);
    }
  }
  if (Array.isArray(profile.education)) {
    for (const ed of profile.education) {
      const t = [ed.degree, ed.institution].filter(Boolean).join(' — ');
      if (t) lines.push(t);
    }
  }
  const text = lines.join('\n\n').trim() || (profile as { summary?: string }).summary || '';

  return {
    text,
    parsed: data.profile ?? null,
    contact_info: data.contact_info ?? null,
    parsed_at: new Date().toISOString(),
  };
}

function skillsListFromParse(data: ParseResumeResponse): string[] {
  const fromProfile = (data.profile as { skills?: unknown } | undefined)?.skills;
  if (Array.isArray(fromProfile)) {
    return fromProfile.map((s) => String(s)).filter(Boolean);
  }
  const fromChain = data.skills?.skills;
  if (Array.isArray(fromChain)) {
    return fromChain.map((s) => String(s)).filter(Boolean);
  }
  return [];
}

export async function persistParseToProfile(
  userId: string,
  data: ParseResumeResponse
): Promise<{ error: Error | null }> {
  const skills = skillsListFromParse(data);
  const experience = buildExperiencePayload(data);

  const { data: existing, error: selErr } = await supabase
    .from('profiles')
    .select('id')
    .eq('user_id', userId)
    .maybeSingle();

  if (selErr) return { error: selErr };

  if (existing) {
    const { error } = await supabase
      .from('profiles')
      .update({ skills, experience })
      .eq('user_id', userId);
    return { error: error || null };
  }

  const { error } = await supabase.from('profiles').insert({
    id: userId,
    user_id: userId,
    skills,
    experience,
  });
  return { error: error || null };
}

type UploadFormProps = {
  onParsed?: (data: ParseResumeResponse) => void;
  className?: string;
};

export default function UploadForm({ onParsed, className = '' }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<ParseState>('idle');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<ParseResumeResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');
    setResult(null);

    if (!file) {
      setStatus('error');
      setMessage('Choose a PDF or image file first.');
      return;
    }

    setStatus('uploading');

    const sessionRes = await supabase.auth.getSession();
    const userId = sessionRes.data.session?.user?.id;
    if (!userId) {
      setStatus('error');
      setMessage('You must be signed in to parse and save your profile.');
      return;
    }

    const body = new FormData();
    body.append('file', file);

    try {
      const res = await fetch(`${getApiBaseUrl()}/parse/resume`, {
        method: 'POST',
        body,
      });

      const data = (await res.json()) as ParseResumeResponse;

      if (!res.ok) {
        setStatus('error');
        setMessage(
          typeof data === 'object' && data && 'detail' in data
            ? String((data as { detail?: unknown }).detail)
            : `Request failed (${res.status})`
        );
        return;
      }

      if (data.error) {
        setStatus('error');
        setMessage(String(data.error));
        return;
      }

      setResult(data);
      onParsed?.(data);

      setStatus('saving');
      const { error: saveErr } = await persistParseToProfile(userId, data);
      if (saveErr) {
        setStatus('error');
        setMessage(`Parsed OK, but could not save to Supabase: ${saveErr.message}`);
        return;
      }

      setStatus('success');
      setMessage('Profile updated from your resume and saved.');
    } catch (err) {
      setStatus('error');
      setMessage(err instanceof Error ? err.message : 'Network error — is the API running?');
    }
  };

  const profile = result?.profile as
    | {
        name?: string;
        summary?: string;
        skills?: string[];
        education?: unknown[];
        experience?: unknown[];
      }
    | undefined;

  return (
    <div className={`space-y-4 ${className}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-white/80 mb-2">Resume file</label>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-white/80 file:mr-4 file:rounded-lg file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-white hover:file:bg-white/20"
          />
          <p className="text-xs text-white/40 mt-1">PDF or image. Sent to POST /parse/resume, then stored in your profile.</p>
        </div>
        <button
          type="submit"
          disabled={status === 'uploading' || status === 'saving'}
          className="px-5 py-2.5 rounded-xl bg-white text-black font-semibold hover:bg-white/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {status === 'uploading' || status === 'saving' ? 'Processing…' : 'Parse & save profile'}
        </button>
      </form>

      {message && (
        <div
          className={`p-3 rounded-lg text-sm border ${
            status === 'error'
              ? 'border-red-400/30 bg-red-500/10 text-red-200'
              : 'border-emerald-400/30 bg-emerald-500/10 text-emerald-200'
          }`}
        >
          {message}
        </div>
      )}

      {result && profile && status !== 'error' && (
        <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3 text-sm">
          <div className="text-white/90 font-semibold">Parsed profile</div>
          {profile.name && <p className="text-white/80">Name: {profile.name}</p>}
          {profile.summary && <p className="text-white/70 whitespace-pre-wrap">{profile.summary}</p>}
          {Array.isArray(profile.skills) && profile.skills.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {profile.skills.map((s) => (
                <span key={s} className="px-2 py-0.5 rounded-md bg-white/10 text-white/85 text-xs">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
