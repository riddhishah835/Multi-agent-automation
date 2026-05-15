const MAP = {
  high: 'severity--high',
  medium: 'severity--medium',
  low: 'severity--low',
  critical: 'severity--critical',
};

export default function SeverityBadge({ level }) {
  const key = (level || '').toLowerCase();
  return <span className={`severity-badge ${MAP[key] || ''}`}>{level}</span>;
}
