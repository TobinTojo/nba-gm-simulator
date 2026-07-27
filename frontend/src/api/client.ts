import type {
  GameGuessResponse,
  GameStartResponse,
  GameStatusResponse,
  HealthResponse,
  InitialsRevealResponse,
  LeaderboardResponse,
  SubmitScoreResponse,
} from '@/types';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Request failed');
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>('/health?mode=all_time'),
  getGameStatus: () => request<GameStatusResponse>('/game/status?mode=all_time'),
  startGame: () =>
    request<GameStartResponse>('/game/start', {
      method: 'POST',
      body: JSON.stringify({ mode: 'all_time' }),
    }),
  submitGuess: (initials: string, guess: string, usedPlayerIds: number[], timeRemaining = 0) =>
    request<GameGuessResponse>('/game/guess', {
      method: 'POST',
      body: JSON.stringify({
        initials,
        guess,
        used_player_ids: usedPlayerIds,
        mode: 'all_time',
        time_remaining: timeRemaining,
      }),
    }),
  revealInitials: (initialsList: string[]) =>
    request<InitialsRevealResponse>('/game/reveal', {
      method: 'POST',
      body: JSON.stringify({
        initials_list: initialsList,
        mode: 'all_time',
      }),
    }),
  getLeaderboard: (limit = 25, accessToken?: string) =>
    request<LeaderboardResponse>(`/leaderboard?limit=${limit}`, {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    }),
  submitLeaderboardScore: (score: number, accessToken: string) =>
    request<SubmitScoreResponse>('/leaderboard/submit', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ score }),
    }),
};
