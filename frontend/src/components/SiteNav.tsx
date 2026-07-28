import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { ProfileResponse } from '@/types';
import type { Session, User } from '@supabase/supabase-js';

interface SiteNavProps {
  mode: 'home' | 'solo' | 'versus';
  onGoHome: () => void;
  onPlaySolo: () => void;
  onPlayFriends: () => void;
  onScrollAbout: () => void;
  enabled: boolean;
  user: User | null;
  session: Session | null;
  authLoading: boolean;
  signInWithGoogle: (pendingScore?: number) => Promise<void>;
  signOut: () => Promise<void>;
  profileRefreshKey?: number;
}

export function SiteNav({
  mode,
  onGoHome,
  onPlaySolo,
  onPlayFriends,
  onScrollAbout,
  enabled,
  user,
  session,
  authLoading,
  signInWithGoogle,
  signOut,
  profileRefreshKey = 0,
}: SiteNavProps) {
  const [open, setOpen] = useState(false);
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const displayName =
    user?.user_metadata?.full_name ??
    user?.user_metadata?.name ??
    user?.user_metadata?.user_name ??
    user?.email?.split('@')[0] ??
    'Player';

  const avatarUrl =
    (typeof user?.user_metadata?.avatar_url === 'string' && user.user_metadata.avatar_url) ||
    (typeof user?.user_metadata?.picture === 'string' && user.user_metadata.picture) ||
    null;

  const loadProfile = useCallback(async () => {
    if (!session?.access_token) {
      setProfile(null);
      return;
    }
    setProfileLoading(true);
    try {
      const next = await api.getProfile(session.access_token);
      setProfile(next);
    } catch {
      setProfile({
        display_name: displayName,
        high_score: 0,
        friendly_wins: 0,
        rank: null,
        updated_at: null,
      });
    } finally {
      setProfileLoading(false);
    }
  }, [session?.access_token, displayName]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile, profileRefreshKey]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, []);

  return (
    <header className="site-nav sticky top-0 z-40 border-b border-white/5 bg-court-950/75 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <button type="button" onClick={onGoHome} className="group flex items-center gap-3 text-left">
          <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-accent shadow-[0_0_24px_rgba(249,115,22,0.35)]">
            <img src="/basketball.svg" alt="" className="h-6 w-6 transition group-hover:rotate-45" />
          </span>
          <span>
            <span className="block font-display text-lg leading-none tracking-wide text-white sm:text-xl">
              NAME RUSH
            </span>
            <span className="mt-0.5 hidden text-[10px] uppercase tracking-[0.28em] text-slate-500 sm:block">
              NBA Initials
            </span>
          </span>
        </button>

        <nav className="hidden items-center gap-1 md:flex">
          <button
            type="button"
            onClick={onPlaySolo}
            className={`nav-link ${mode === 'solo' ? 'nav-link-active' : ''}`}
          >
            Solo
          </button>
          <button
            type="button"
            onClick={onPlayFriends}
            className={`nav-link ${mode === 'versus' ? 'nav-link-active' : ''}`}
          >
            Friends
          </button>
          {mode === 'home' && (
            <button type="button" onClick={onScrollAbout} className="nav-link">
              About
            </button>
          )}
        </nav>

        <div className="relative flex items-center gap-2" ref={menuRef}>
          {!enabled ? null : authLoading ? (
            <span className="text-xs text-slate-500">…</span>
          ) : user ? (
            <>
              <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pl-1 pr-3 transition hover:border-accent/40 hover:bg-white/10"
                aria-expanded={open}
                aria-haspopup="menu"
              >
                {avatarUrl ? (
                  <img src={avatarUrl} alt="" className="h-8 w-8 rounded-full object-cover" />
                ) : (
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20 text-xs font-semibold text-accent">
                    {displayName.slice(0, 1).toUpperCase()}
                  </span>
                )}
                <span className="hidden max-w-[8rem] truncate text-sm text-slate-200 sm:inline">
                  {displayName}
                </span>
              </button>

              {open && (
                <div
                  role="menu"
                  className="absolute right-0 top-[calc(100%+0.6rem)] w-72 overflow-hidden rounded-2xl border border-white/10 bg-court-900/95 p-4 shadow-2xl shadow-black/40 backdrop-blur-xl animate-slide-up"
                >
                  <p className="truncate text-sm font-semibold text-white">{profile?.display_name || displayName}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{user.email}</p>

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-xl bg-court-800/80 px-3 py-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Best</p>
                      <p className="mt-1 font-display text-2xl text-white">
                        {profileLoading ? '—' : (profile?.high_score ?? 0)}
                      </p>
                      <p className="text-xs text-slate-500">solo pts</p>
                    </div>
                    <div className="rounded-xl bg-court-800/80 px-3 py-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">1v1</p>
                      <p className="mt-1 font-display text-2xl text-accent">
                        {profileLoading ? '—' : (profile?.friendly_wins ?? 0)}
                      </p>
                      <p className="text-xs text-slate-500">friendly wins</p>
                    </div>
                  </div>

                  {profile?.rank != null && (
                    <p className="mt-3 text-xs text-slate-400">
                      Global rank <span className="text-white">#{profile.rank}</span>
                    </p>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      void signOut();
                    }}
                    className="mt-4 w-full rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:border-red-400/40 hover:text-red-300"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={() => void signInWithGoogle()}
              className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-court-950 transition hover:bg-slate-100"
            >
              Sign in
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
