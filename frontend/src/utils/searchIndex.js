import {
  auditHistory,
  evidenceItems,
  findings,
  highRiskVendors,
  pendingApprovals,
  recentAudits,
} from '../data/mockData';

const PAGES = [
  { label: 'Audit Queue', path: '/', keywords: 'home dashboard audits queue' },
  { label: 'Upload Documents', path: '/upload', keywords: 'upload soc2 iso contract aml' },
  { label: 'Audit Pipeline', path: '/pipeline', keywords: 'workflow progress pipeline ocr reader judge' },
  { label: 'Findings', path: '/findings', keywords: 'risks compliance findings severity' },
  { label: 'Evidence Viewer', path: '/evidence', keywords: 'evidence quote source page' },
  { label: 'Human Review', path: '/review', keywords: 'hitl approval reject review' },
  { label: 'Reports', path: '/reports', keywords: 'download pdf csv json report' },
  { label: 'Audit History', path: '/history', keywords: 'history past audits search' },
  { label: 'System Health', path: '/observability', keywords: 'latency qdrant observability health' },
  { label: 'Settings', path: '/settings', keywords: 'tenant frameworks thresholds config' },
];

export function buildSearchIndex(uploads = []) {
  const items = [...PAGES];

  highRiskVendors.forEach((v) => {
    items.push({
      id: `vendor-${v.name}`,
      type: 'Vendor',
      label: v.name,
      subtitle: `Risk ${v.riskScore} · ${v.framework}`,
      path: '/findings',
      keywords: `${v.name} ${v.framework} ${v.status} vendor`.toLowerCase(),
    });
  });

  recentAudits.forEach((a) => {
    items.push({
      id: a.id,
      type: 'Audit',
      label: `${a.id} — ${a.vendor}`,
      subtitle: a.status.replace(/_/g, ' '),
      path: a.status === 'pending_review' ? '/review' : '/pipeline',
      keywords: `${a.id} ${a.vendor} ${a.risk} ${a.status}`.toLowerCase(),
    });
  });

  auditHistory.forEach((a) => {
    items.push({
      id: `hist-${a.id}`,
      type: 'History',
      label: `${a.vendor} (${a.id})`,
      subtitle: `${a.date} · ${a.framework}`,
      path: '/history',
      keywords: `${a.id} ${a.vendor} ${a.framework} ${a.risk} ${a.outcome}`.toLowerCase(),
    });
  });

  pendingApprovals.forEach((a) => {
    items.push({
      id: `pending-${a.id}`,
      type: 'Review',
      label: a.vendor,
      subtitle: `Waiting approval · ${a.id}`,
      path: '/review',
      keywords: `${a.vendor} ${a.id} ${a.aiRecommendation} approval`.toLowerCase(),
    });
  });

  findings.forEach((f) => {
    items.push({
      id: f.id,
      type: 'Finding',
      label: f.finding,
      subtitle: `${f.severity} · ${f.framework}`,
      path: '/findings',
      keywords: `${f.id} ${f.finding} ${f.category} ${f.framework} ${f.severity}`.toLowerCase(),
    });
  });

  evidenceItems.forEach((e) => {
    items.push({
      id: `ev-${e.id}`,
      type: 'Evidence',
      label: e.quote.slice(0, 60),
      subtitle: `${e.source} · page ${e.page}`,
      path: '/evidence',
      keywords: `${e.quote} ${e.source} ${e.category} ${e.findingId}`.toLowerCase(),
    });
  });

  uploads.forEach((u) => {
    items.push({
      id: `file-${u.id}`,
      type: 'Document',
      label: u.name,
      subtitle: u.type,
      path: '/upload',
      keywords: `${u.name} ${u.type} upload document`.toLowerCase(),
    });
  });

  return items;
}

export function searchItems(index, query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];

  return index
    .filter((item) => {
      const hay = `${item.label} ${item.subtitle || ''} ${item.keywords || ''}`.toLowerCase();
      return q.split(/\s+/).every((term) => hay.includes(term));
    })
    .slice(0, 12);
}
