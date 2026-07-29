import type {
  GameGuessResponse,
  GameStartResponse,
  GameStatusResponse,
  HealthResponse,
  InitialsRevealResponse,
  LeaderboardResponse,
  MultiplayerRoomResponse,
  ProfileResponse,
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
  getProfile: (accessToken: string) =>
    request<ProfileResponse>('/leaderboard/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    }),
  recordCareerGame: (
    score: number,
    correct: number,
    attempts: number,
    accessToken: string,
  ) =>
    request<ProfileResponse>('/leaderboard/career', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ score, correct, attempts }),
    }),
  createMultiplayerRoom: (accessToken: string, totalRounds = 9, era = 'all_time') =>
    request<MultiplayerRoomResponse>('/multiplayer/create', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ total_rounds: totalRounds, era }),
    }),
  joinMultiplayerRoom: (code: string, accessToken: string) =>
    request<MultiplayerRoomResponse>('/multiplayer/join', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ code }),
    }),
  setMultiplayerSettings: (
    code: string,
    accessToken: string,
    settings: { totalRounds?: number; era?: string },
  ) =>
    request<MultiplayerRoomResponse>('/multiplayer/rounds', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({
        code,
        total_rounds: settings.totalRounds,
        era: settings.era,
      }),
    }),
  startMultiplayerMatch: (code: string, accessToken: string) =>
    request<MultiplayerRoomResponse>('/multiplayer/start', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ code }),
    }),
  rematchMultiplayer: (code: string, accessToken: string) =>
    request<MultiplayerRoomResponse>('/multiplayer/rematch', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ code }),
    }),
  leaveMultiplayerRoom: (code: string, accessToken: string) =>
    request<MultiplayerRoomResponse>('/multiplayer/leave', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ code }),
    }),
  getMultiplayerRoom: (code: string, accessToken: string) =>
    request<MultiplayerRoomResponse>(`/multiplayer/room/${encodeURIComponent(code)}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    }),
  passMultiplayerRound: (code: string, accessToken: string) =>
    request<MultiplayerRoomResponse>('/multiplayer/pass', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ code }),
    }),
  submitMultiplayerGuess: (code: string, guess: string, accessToken: string) =>
    request<MultiplayerRoomResponse>('/multiplayer/guess', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ code, guess }),
    }),
};
