const MAP = {
  running: 'status--running',
  completed: 'status--completed',
  pending_review: 'status--pending',
  waiting_approval: 'status--pending',
  failed: 'status--failed',
  approved: 'status--completed',
  rejected: 'status--failed',
  conditional: 'status--warning',
};

export default function StatusBadge({ status }) {
  const label = (status || '').replace(/_/g, ' ');
  return <span className={`status-badge ${MAP[status] || ''}`}>{label}</span>;
}
