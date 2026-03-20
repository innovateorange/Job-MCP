"use client";

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

type ProfileRow = {
  skills: unknown;
  experience: unknown;
} | null;

type PreferencesRow = {
  job_types: unknown;
} | null;

function toCommaString(value: unknown): string {
  if (!value) return '';
  if (Array.isArray(value)) return value.map((v) => String(v)).join(', ');
  if (typeof value === 'string') return value;
  return '';
}

function parseSkillsInput(input: string): string[] {
  return input
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
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
    // Common shape we store: { text: "..." }
    const maybeObj = value as any;
    if (typeof maybeObj.text === 'string') return maybeObj.text;
    if (typeof maybeObj.experience === 'string') return maybeObj.experience;
  }
  return '';
}

export default function Profile() {
  const router = useRouter();

  const [authLoading, setAuthLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  const [userId, setUserId] = useState<string | null>(null);

  const [skillsInput, setSkillsInput] = useState('');
  const [experienceInput, setExperienceInput] = useState('');
  const [jobTypesInput, setJobTypesInput] = useState('');

  // Used for "Cancel" to restore what was loaded from Supabase
  const [initialSkillsInput, setInitialSkillsInput] = useState('');
  const [initialExperienceInput, setInitialExperienceInput] = useState('');
  const [initialJobTypesInput, setInitialJobTypesInput] = useState('');

  const savePayload = useMemo(() => {
    const skills = parseSkillsInput(skillsInput);
    const experience = { text: experienceInput.trim() };
    const job_types = parseJobTypesInput(jobTypesInput);
    return { skills, experience, job_types };
  }, [skillsInput, experienceInput, jobTypesInput]);

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

      // Load existing profile
      const { data: profileData, error: profileErr } = await supabase
        .from('profiles')
        .select('skills,experience')
        .eq('user_id', session.user.id)
        .maybeSingle();

      if (profileErr) {
        setError(profileErr.message);
        setAuthLoading(false);
        return;
      }

      const profileRow: ProfileRow = profileData ?? null;
      setSkillsInput(toCommaString((profileRow as any)?.skills));
      setExperienceInput(toExperienceText((profileRow as any)?.experience));
      const nextSkillsInput = toCommaString((profileRow as any)?.skills);
      const nextExperienceInput = toExperienceText((profileRow as any)?.experience);
      setInitialSkillsInput(nextSkillsInput);
      setInitialExperienceInput(nextExperienceInput);

      // Load existing preferences
      const { data: prefData, error: prefErr } = await supabase
        .from('preferences')
        .select('job_types')
        .eq('user_id', session.user.id)
        .maybeSingle();

      if (prefErr) {
        setError(prefErr.message);
        setAuthLoading(false);
        return;
      }

      const prefRow: PreferencesRow = prefData ?? null;
      setJobTypesInput(toCommaString((prefRow as any)?.job_types));
      const nextJobTypesInput = toCommaString((prefRow as any)?.job_types);
      setInitialJobTypesInput(nextJobTypesInput);

      setEditMode(false);

      setAuthLoading(false);
    };

    init();
  }, [router]);

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      // Upsert-ish for profiles (insert with deterministic ID if absent)
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
        // If your `profiles.id` doesn't have a default, we set it to `user_id` to avoid null inserts.
        const { error: insertErr } = await supabase.from('profiles').insert({
          id: userId,
          user_id: userId,
          skills: savePayload.skills,
          experience: savePayload.experience,
        });

        if (insertErr) throw insertErr;
      }

      // Upsert-ish for preferences
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
      // Treat the saved values as the new "loaded" state for cancel/reset.
      setInitialSkillsInput(skillsInput);
      setInitialExperienceInput(experienceInput);
      setInitialJobTypesInput(jobTypesInput);
      setEditMode(false);
    } catch (e: any) {
      setError(e?.message || 'Failed to save profile. Check Supabase logs/RLS policies.');
    } finally {
      setSaving(false);
    }
  };

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
            Update your skills, experience, and job types. These are used by the auto-apply flow.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-green-300 text-sm">
            {success}
          </div>
        )}

        <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div className="text-white/80 font-semibold">
              {editMode ? 'Editing profile' : 'View profile'}
            </div>
            {!editMode ? (
              <button
                type="button"
                onClick={() => {
                  setError('');
                  setSuccess('');
                  setSkillsInput(initialSkillsInput);
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
                    setSkillsInput(initialSkillsInput);
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
              <label className="block text-sm font-medium text-white/80">Skills (comma separated)</label>
              <textarea
                value={skillsInput}
                onChange={(e) => setSkillsInput(e.target.value)}
                rows={4}
                placeholder="python, sql, postgres, react, aws"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/30 focus:bg-white/10 transition-all"
                disabled={!editMode}
              />
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

        <div className="mt-6 text-sm text-white/50">
          Note: resume upload + parsing can be added next once the `/parse/resume` backend endpoint is implemented.
        </div>
      </div>
    </main>
  );
}
