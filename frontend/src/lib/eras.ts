export const ERA_OPTIONS = [
  { value: 'all_time', label: 'All-time' },
  { value: '60s', label: '1960s' },
  { value: '70s', label: '1970s' },
  { value: '80s', label: '1980s' },
  { value: '90s', label: '1990s' },
  { value: '2000s', label: '2000s' },
  { value: '2010s', label: '2010s' },
  { value: '2020s', label: '2020s' },
] as const;

export type EraValue = (typeof ERA_OPTIONS)[number]['value'];

export function eraLabel(era: string | null | undefined): string {
  return ERA_OPTIONS.find((option) => option.value === era)?.label ?? 'All-time';
}
