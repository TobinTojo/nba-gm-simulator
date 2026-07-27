import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type {
  DraftPickSummary,
  PlayerSummary,
  TeamSummary,
  TradeEvaluation,
  TradeInboxItem,
} from '@/types';

export function TradesPage() {
  const [inbox, setInbox] = useState<TradeInboxItem[]>([]);
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [myRoster, setMyRoster] = useState<PlayerSummary[]>([]);
  const [partnerRoster, setPartnerRoster] = useState<PlayerSummary[]>([]);
  const [myPicks, setMyPicks] = useState<DraftPickSummary[]>([]);
  const [partnerId, setPartnerId] = useState<number | null>(null);
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [sendPlayers, setSendPlayers] = useState<number[]>([]);
  const [receivePlayers, setReceivePlayers] = useState<number[]>([]);
  const [sendPicks, setSendPicks] = useState<number[]>([]);
  const [evaluation, setEvaluation] = useState<TradeEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const [hub, allTeams, picks, inboxItems] = await Promise.all([
        api.getTeamHub(),
        api.getTeams(),
        api.getMyPicks(),
        api.getTradeInbox(),
      ]);
      setMyTeamId(hub.team.id);
      setMyRoster(hub.roster);
      setTeams(allTeams.filter((t) => t.id !== hub.team.id));
      setMyPicks(picks);
      setInbox(inboxItems);
      setLoading(false);
    }
    void load().catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!partnerId) return;
    void api.getRoster(partnerId).then(setPartnerRoster);
  }, [partnerId]);

  function toggle(id: number, list: number[], setter: (v: number[]) => void) {
    setter(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  }

  async function handleEvaluate() {
    if (!partnerId) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.evaluateTrade({
        partner_team_id: partnerId,
        send_player_ids: sendPlayers,
        receive_player_ids: receivePlayers,
        send_pick_ids: sendPicks,
        receive_pick_ids: [],
      });
      setEvaluation(result);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Evaluation failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleExecute() {
    if (!partnerId) return;
    setBusy(true);
    try {
      const result = await api.executeTrade({
        partner_team_id: partnerId,
        send_player_ids: sendPlayers,
        receive_player_ids: receivePlayers,
        send_pick_ids: sendPicks,
        receive_pick_ids: [],
      });
      setMessage(result.message);
      setEvaluation(result.evaluation);
      const hub = await api.getTeamHub();
      setMyRoster(hub.roster);
      setSendPlayers([]);
      setReceivePlayers([]);
      setSendPicks([]);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Trade failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleInboxResponse(offerId: number, accept: boolean) {
    setBusy(true);
    try {
      const result = await api.respondTradeOffer(offerId, accept);
      setMessage(result.message);
      setInbox(await api.getTradeInbox());
      const hub = await api.getTeamHub();
      setMyRoster(hub.roster);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingSpinner message="Loading trade center..." />;

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <Link to="/hub" className="text-sm text-slate-500 hover:text-accent">← Back to Hub</Link>
        <h1 className="mt-2 text-3xl font-bold text-white">Trade Center</h1>
        <p className="text-slate-400">Build offers — AI evaluates fairness, salary, and roster fit.</p>
      </div>

      {message && <p className="text-sm text-accent">{message}</p>}

      {inbox.length > 0 && (
        <div className="card p-5">
          <h2 className="font-bold text-white">Trade Inbox</h2>
          <ul className="mt-3 space-y-3">
            {inbox.map((offer) => (
              <li key={offer.id} className="flex flex-col gap-2 border-b border-court-800/60 pb-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{offer.from_team_name}</p>
                  <p className="text-sm text-slate-400">{offer.message}</p>
                </div>
                <div className="flex gap-2">
                  <button type="button" disabled={busy} onClick={() => void handleInboxResponse(offer.id, true)} className="btn-primary text-xs">Accept</button>
                  <button type="button" disabled={busy} onClick={() => void handleInboxResponse(offer.id, false)} className="btn-secondary text-xs">Decline</button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-4">
          <h2 className="font-bold text-white">You Send</h2>
          <div className="mt-3 max-h-64 space-y-1 overflow-y-auto">
            {myRoster.map((p) => (
              <label key={p.id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={sendPlayers.includes(p.id)}
                  onChange={() => toggle(p.id, sendPlayers, setSendPlayers)}
                  className="accent-accent"
                />
                <span className="text-white">{p.first_name} {p.last_name}</span>
                <span className="text-accent">({p.overall_rating.toFixed(0)})</span>
              </label>
            ))}
          </div>
          <h3 className="mt-4 text-xs uppercase text-slate-500">Draft Picks</h3>
          {myPicks.map((pick) => (
            <label key={pick.id} className="mt-1 flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={sendPicks.includes(pick.id)}
                onChange={() => toggle(pick.id, sendPicks, setSendPicks)}
                className="accent-accent"
              />
              <span className="text-slate-300">{pick.season} R{pick.round_number}</span>
            </label>
          ))}
        </div>

        <div className="card p-4">
          <label className="text-xs uppercase text-slate-500">Trade Partner</label>
          <select
            value={partnerId ?? ''}
            onChange={(e) => setPartnerId(Number(e.target.value))}
            className="mt-1 w-full rounded border border-court-600 bg-court-800 px-3 py-2 text-white"
          >
            <option value="">Select team...</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>{t.city} {t.name}</option>
            ))}
          </select>

          <div className="mt-4 flex flex-col gap-2">
            <button type="button" onClick={() => void handleEvaluate()} disabled={busy || !partnerId} className="btn-secondary">
              Evaluate Trade
            </button>
            <button type="button" onClick={() => void handleExecute()} disabled={busy || !evaluation?.accepted} className="btn-primary">
              Execute Trade
            </button>
          </div>

          {evaluation && (
            <div className="mt-4 rounded-lg border border-court-600 bg-court-800/50 p-3 text-sm">
              <p className={evaluation.accepted ? 'text-emerald-400' : 'text-red-400'}>
                {evaluation.reason}
              </p>
              <p className="mt-2 text-slate-400">Fairness: {evaluation.fairness_score}%</p>
              <p className="text-slate-400">Salary legal: {evaluation.salary_legal ? 'Yes' : 'No'}</p>
              <p className="text-slate-400">Roster fit: {evaluation.roster_fit_score}</p>
            </div>
          )}
          {message && <p className="mt-3 text-sm text-accent">{message}</p>}
        </div>

        <div className="card p-4">
          <h2 className="font-bold text-white">You Receive</h2>
          <div className="mt-3 max-h-64 space-y-1 overflow-y-auto">
            {partnerRoster.map((p) => (
              <label key={p.id} className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={receivePlayers.includes(p.id)}
                  onChange={() => toggle(p.id, receivePlayers, setReceivePlayers)}
                  className="accent-accent"
                />
                <span className="text-white">{p.first_name} {p.last_name}</span>
                <span className="text-accent">({p.overall_rating.toFixed(0)})</span>
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
