import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface AttributeChartProps {
  attributes: {
    label: string;
    value: number;
  }[];
}

export function AttributeChart({ attributes }: AttributeChartProps) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={attributes} layout="vertical" margin={{ left: 20, right: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#243650" />
        <XAxis type="number" domain={[0, 99]} stroke="#64748b" fontSize={12} />
        <YAxis type="category" dataKey="label" stroke="#64748b" fontSize={12} width={90} />
        <Tooltip
          contentStyle={{ background: '#151f2e', border: '1px solid #243650', borderRadius: 8 }}
          labelStyle={{ color: '#f1f5f9' }}
        />
        <Bar dataKey="value" fill="#f97316" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

interface RatingHistoryChartProps {
  data: { season: string; overall_rating: number; potential: number }[];
}

export function RatingHistoryChart({ data }: RatingHistoryChartProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#243650" />
        <XAxis dataKey="season" stroke="#64748b" fontSize={11} />
        <YAxis domain={[60, 99]} stroke="#64748b" fontSize={12} />
        <Tooltip
          contentStyle={{ background: '#151f2e', border: '1px solid #243650', borderRadius: 8 }}
        />
        <Line type="monotone" dataKey="overall_rating" stroke="#f97316" strokeWidth={2} dot />
        <Line type="monotone" dataKey="potential" stroke="#34d399" strokeWidth={2} strokeDasharray="4 4" dot />
      </LineChart>
    </ResponsiveContainer>
  );
}

interface StatTrendChartProps {
  data: { label: string; ppg: number; rpg: number; apg: number }[];
}

export function StatTrendChart({ data }: StatTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#243650" />
        <XAxis dataKey="label" stroke="#64748b" fontSize={12} />
        <YAxis stroke="#64748b" fontSize={12} />
        <Tooltip
          contentStyle={{ background: '#151f2e', border: '1px solid #243650', borderRadius: 8 }}
        />
        <Bar dataKey="ppg" fill="#f97316" name="PPG" />
        <Bar dataKey="rpg" fill="#60a5fa" name="RPG" />
        <Bar dataKey="apg" fill="#34d399" name="APG" />
      </BarChart>
    </ResponsiveContainer>
  );
}
