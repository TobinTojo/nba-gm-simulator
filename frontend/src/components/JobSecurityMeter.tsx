interface JobSecurityMeterProps {
  security: number;
  status: string;
  ownerExpectations: string;
}

export function JobSecurityMeter({ security, status, ownerExpectations }: JobSecurityMeterProps) {
  const color =
    security >= 80 ? 'bg-emerald-500' : security >= 60 ? 'bg-blue-500' : security >= 40 ? 'bg-yellow-500' : security >= 20 ? 'bg-orange-500' : 'bg-red-500';

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500">Job Security</p>
          <p className="mt-1 text-2xl font-bold text-white">{security.toFixed(0)}%</p>
          <p className={`text-sm font-medium ${security >= 60 ? 'text-emerald-400' : security >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
            {status}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase text-slate-500">Owner Expects</p>
          <p className="text-sm font-semibold text-white">{ownerExpectations}</p>
        </div>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-court-800">
        <div className={`h-full transition-all ${color}`} style={{ width: `${security}%` }} />
      </div>
    </div>
  );
}
