'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import UploadForm from '@/components/UploadForm';

type ExperienceShape = {
  text?: string;
  parsed?: Record<string, unknown>;
  contact_info?: unknown;
  parsed_at?: string;
} | null;

type PreferencesRow = {
  job_types: unknown;
} | null;

function normalizeSkills(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((v) => String(v).trim()).filter(Boolean);
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

function toCommaString(value: unknown): string {
  if (!value) return '';
  if (Array.isArray(value)) return value.map((v) => String(v)).join(', ');
  if (typeof value === 'string') return value;
  return '';
}

function parseJobTypesInput(input: string): string[] {
  return input
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function toExperienceText(value: unknown): string {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'object') {
    const maybeObj = value as { text?: string; experience?: string };
    if (typeof maybeObj.text === 'string') return maybeObj.text;
    if (typeof maybeObj.experience === 'string') return maybeObj.experience;
  }
  return '';
}

function getExperienceObject(value: unknown): ExperienceShape {
  if (!value || typeof value !== 'object') return null;
  return value as ExperienceShape;
}

export default function Profile() {
  const router = useRouter();

  const [authLoading, setAuthLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [userId, setUserId] = useState<string | null>(null);

  const [skillTags, setSkillTags] = useState<string[]>([]);
  const [skillDraft, setSkillDraft] = useState('');
  const [experienceInput, setExperienceInput] = useState('');
  const [jobTypesInput, setJobTypesInput] = useState('');
  const [parsedFromDb, setParsedFromDb] = useState<Record<string, unknown> | null>(null);

  const [initialSkillTags, setInitialSkillTags] = useState<string[]>([]);
  const [initialExperienceInput, setInitialExperienceInput] = useState('');
  const [initialJobTypesInput, setInitialJobTypesInput] = useState('');

  const loadProfile = useCallback(async (uid: string) => {
    const { data: profileData, error: profileErr } = await supabase
      .from('profiles')
      .select('skills, experience')
      .eq('user_id', uid)
      .maybeSingle();

    if (profileErr) throw profileErr;

    const skills = normalizeSkills((profileData as { skills?: unknown } | null)?.skills);
    setSkillTags(skills);
    setInitialSkillTags(skills);

    const expObj = getExperienceObject((profileData as { experience?: unknown } | null)?.experience);
    setExperienceInput(toExperienceText((profileData as { experience?: unknown } | null)?.experience));
    setInitialExperienceInput(toExperienceText((profileData as { experience?: unknown } | null)?.experience));
    if (expObj?.parsed && typeof expObj.parsed === 'object') {
      setParsedFromDb(expObj.parsed as Record<string, unknown>);
    } else {
      setParsedFromDb(null);
    }

    const { data: prefData, error: prefErr } = await supabase.from('preferences').select('job_types').eq('user_id', uid).maybeSingle();

    if (prefErr) throw prefErr;

    const jt = toCommaString((prefData as PreferencesRow)?.job_types);
    setJobTypesInput(jt);
    setInitialJobTypesInput(jt);
  }, []);

  const savePayload = useMemo(() => {
    const experience: Record<string, unknown> = { text: experienceInput.trim() };
    if (parsedFromDb) experience.parsed = parsedFromDb;
    return { skills: skillTags, experience, job_types: parseJobTypesInput(jobTypesInput) };
  }, [skillTags, experienceInput, jobTypesInput, parsedFromDb]);

  useEffect(() => {
    const init = async () => {
      setError('');
      setSuccess('');
      setAuthLoading(true);

      const { data } = await supabase.auth.getSession();
      const session = data.session;

      if (!session?.user) {
        router.push('/login');
        return;
      }

      setUserId(session.user.id);

      try {
        await loadProfile(session.user.id);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load profile');
        setAuthLoading(false);
        return;
      }

      setEditMode(false);
      setAuthLoading(false);
    };

    init();
  }, [router, loadProfile]);

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const { data: existingProfile, error: existingProfileErr } = await supabase
        .from('profiles')
        .select('id')
        .eq('user_id', userId)
        .maybeSingle();

      if (existingProfileErr) throw existingProfileErr;

      if (existingProfile) {
        const { error: updateErr } = await supabase
          .from('profiles')
          .update({
            skills: savePayload.skills,
            experience: savePayload.experience,
          })
          .eq('user_id', userId);

        if (updateErr) throw updateErr;
      } else {
        const { error: insertErr } = await supabase.from('profiles').insert({
          id: userId,
          user_id: userId,
          skills: savePayload.skills,
          experience: savePayload.experience,
        });

        if (insertErr) throw insertErr;
      }

      const { data: existingPref, error: existingPrefErr } = await supabase
        .from('preferences')
        .select('id')
        .eq('user_id', userId)
        .maybeSingle();

      if (existingPrefErr) throw existingPrefErr;

      if (existingPref) {
        const { error: prefUpdateErr } = await supabase
          .from('preferences')
          .update({ job_types: savePayload.job_types })
          .eq('user_id', userId);

        if (prefUpdateErr) throw prefUpdateErr;
      } else {
        const { error: prefInsertErr } = await supabase.from('preferences').insert({
          id: userId,
          user_id: userId,
          job_types: savePayload.job_types,
        });

        if (prefInsertErr) throw prefInsertErr;
      }

      setSuccess('Profile saved.');
      setInitialSkillTags([...skillTags]);
      setInitialExperienceInput(experienceInput);
      setInitialJobTypesInput(jobTypesInput);
      setEditMode(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save profile. Check Supabase logs/RLS policies.');
    } finally {
      setSaving(false);
    }
  };

  const addSkillTag = () => {
    const next = skillDraft.trim();
    if (!next || skillTags.includes(next)) return;
    setSkillTags((s) => [...s, next]);
    setSkillDraft('');
  };

  const removeSkillTag = (tag: string) => {
    setSkillTags((s) => s.filter((t) => t !== tag));
  };

  const onResumeParsed = useCallback(async () => {
    if (!userId) return;
    setSuccess('Resume parsed and saved to your profile.');
    try {
      await loadProfile(userId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to refresh profile after parse');
    }
  }, [userId, loadProfile]);

  if (authLoading) {
    return (
      <main className="min-h-screen bg-black text-white flex items-center justify-center px-6">
        <div>Loading...</div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white pt-24 px-6">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Profile Management</h1>
          <p className="text-white/60">
            Upload a resume to parse with AI, edit skills as tags, and tune preferences for auto-apply.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-sm">{error}</div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-300 text-sm">{success}</div>
        )}

        <section className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-white mb-4">Resume upload</h2>
          <UploadForm onParsed={onResumeParsed} />
        </section>

        {parsedFromDb && (
          <section className="backdrop-blur-xl bg-emerald-500/5 border border-emerald-400/20 rounded-2xl p-6 mb-8">
            <h3 className="text-md font-semibold text-emerald-100 mb-3">Stored parsed profile snapshot</h3>
            <pre className="text-xs text-white/70 overflow-x-auto whitespace-pre-wrap max-h-64 rounded-lg bg-black/40 p-4 border border-white/10">
              {JSON.stringify(parsedFromDb, null, 2)}
            </pre>
          </section>
        )}

        <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div className="text-white/80 font-semibold">{editMode ? 'Editing profile' : 'View profile'}</div>
            {!editMode ? (
              <button
                type="button"
                onClick={() => {
                  setError('');
                  setSuccess('');
                  setSkillTags([...initialSkillTags]);
                  setExperienceInput(initialExperienceInput);
                  setJobTypesInput(initialJobTypesInput);
                  setEditMode(true);
                }}
                className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-all"
              >
                Edit profile
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setError('');
                    setSuccess('');
                    setSkillTags([...initialSkillTags]);
                    setExperienceInput(initialExperienceInput);
                    setJobTypesInput(initialJobTypesInput);
                    setEditMode(false);
                  }}
                  disabled={saving}
                  className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white/80 hover:bg-white/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 rounded-xl bg-white text-black font-semibold hover:bg-white/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving...' : 'Save changes'}
                </button>
              </div>
            )}
          </div>

          <div className="space-y-5">
            <section className="space-y-2">
              <label className="block text-sm font-medium text-white/80">Skills</label>
              {!editMode ? (
                <div className="flex flex-wrap gap-2 min-h-[2.5rem]">
                  {skillTags.length ? (
                    skillTags.map((s) => (
                      <span
                        key={s}
                        className="px-2.5 py-1 rounded-lg bg-white/10 border border-white/10 text-sm text-white/90"
                      >
                        {s}
                      </span>
                    ))
                  ) : (
                    <span className="text-white/40 text-sm">No skills yet — parse a resume or edit your profile.</span>
                  )}
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {skillTags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white/10 border border-white/15 text-sm"
                      >
                        {tag}
                        <button type="button" className="text-white/60 hover:text-white ml-1" onClick={() => removeSkillTag(tag)}>
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={skillDraft}
                      onChange={(e) => setSkillDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addSkillTag();
                        }
                      }}
                      placeholder="Type a skill, press Enter"
                      className="flex-1 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40"
                    />
                    <button
                      type="button"
                      onClick={addSkillTag}
                      className="px-4 py-2 rounded-xl bg-white/10 border border-white/15 text-white hover:bg-white/15"
                    >
                      Add
                    </button>
                  </div>
                </>
              )}
            </section>

            <section className="space-y-2">
              <label className="block text-sm font-medium text-white/80">Experience (free text)</label>
              <textarea
                value={experienceInput}
                onChange={(e) => setExperienceInput(e.target.value)}
                rows={6}
                placeholder="Add roles, projects, responsibilities, achievements..."
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all"
                disabled={!editMode}
              />
            </section>

            <section className="space-y-2">
              <label className="block text-sm font-medium text-white/80">Job types (comma separated)</label>
              <input
                value={jobTypesInput}
                onChange={(e) => setJobTypesInput(e.target.value)}
                placeholder="Full-time, Internship, Remote"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all"
                disabled={!editMode}
              />
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
