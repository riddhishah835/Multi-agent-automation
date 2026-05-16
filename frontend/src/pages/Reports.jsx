import { useState, useEffect } from 'react';
import { Download, FileJson, FileSpreadsheet, FileText } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import { getAuditState } from '../api/client';
import { useToast } from '../context/ToastContext';

const formats = [
  { id: 'pdf', label: 'PDF Report', desc: 'Executive summary + findings', icon: FileText },
  { id: 'csv', label: 'CSV Export', desc: 'Findings table for spreadsheets', icon: FileSpreadsheet },
  { id: 'json', label: 'JSON Bundle', desc: 'Full audit artifact for integrations', icon: FileJson },
  { id: 'md', label: 'Markdown', desc: 'Readable report for Confluence/wiki', icon: FileText },
];

export default function Reports() {
  const { addToast } = useToast();
  const [realTimeState, setRealTimeState] = useState(null);

  useEffect(() => {
    const auditId = localStorage.getItem('current_audit_id');
    if (!auditId) return;

    const fetchState = async () => {
      try {
        const state = await getAuditState(auditId);
        if (state) setRealTimeState(state);
      } catch (err) {
        // Silently handle
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, []);

  const download = (fmt) => {
    if (!realTimeState) {
      addToast('No audit data available to download', 'error');
      return;
    }

    let content = '';
    let mime = 'text/plain';
    let ext = fmt;

    if (fmt === 'md') {
      content = realTimeState.draft_report || '# No report available';
      mime = 'text/markdown';
    } else if (fmt === 'json') {
      content = JSON.stringify(realTimeState, null, 2);
      mime = 'application/json';
    } else if (fmt === 'csv') {
      const findings = realTimeState.findings || [];
      content = 'Finding ID,Severity,Category,Framework\n' + 
        findings.map(f => `"${f.finding_id}","${f.severity}","${f.issue}","${f.frameworks?.join(', ')}"`).join('\n');
      mime = 'text/csv';
    } else if (fmt === 'pdf') {
      import('jspdf').then(({ jsPDF }) => {
        const doc = new jsPDF();
        const reportText = realTimeState.draft_report || 'No report available';
        const lines = doc.splitTextToSize(reportText, 180);
        doc.text(lines, 10, 10);
        doc.save(`audit-report-${localStorage.getItem('current_audit_id')}.pdf`);
        addToast('Downloaded PDF successfully', 'success');
      }).catch(err => {
        console.error('Failed to load jspdf:', err);
        addToast('Failed to generate PDF', 'error');
      });
      return;
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-report-${localStorage.getItem('current_audit_id')}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addToast(`Downloaded ${fmt.toUpperCase()} successfully`, 'success');
  };

  const currentAudit = {
    id: localStorage.getItem('current_audit_id') || 'Unknown',
    vendor: realTimeState?.vendor_name || 'Unknown Vendor',
    frameworks: ['SOC2'] // We can't pull frameworks from root easily, so we hardcode or pull from first finding
  };

  const riskScore = {
    overall: realTimeState?.risk_score || 0,
    recommendation: realTimeState?.risk_score > 70 ? 'Reject (High Risk)' : 'Approve (Low Risk)'
  };

  return (
    <>
      <PageHeader
        title="Final Audit Report"
        subtitle={`${currentAudit.vendor} — ${currentAudit.id}`}
      />

      <article className="card report-summary">
        <section className="report-summary__grid">
          <div>
            <span className="text-muted">Vendor</span>
            <strong>{currentAudit.vendor}</strong>
          </div>
          <div>
            <span className="text-muted">Risk score</span>
            <strong className="text-danger">{riskScore.overall}/100</strong>
          </div>
          <div>
            <span className="text-muted">Recommendation</span>
            <strong>{riskScore.recommendation}</strong>
          </div>
          <div>
            <span className="text-muted">Frameworks</span>
            <strong>{currentAudit.frameworks.join(', ')}</strong>
          </div>
        </section>
      </article>

      <section className="report-formats">
        {formats.map(({ id, label, desc, icon: Icon }) => (
          <article key={id} className="card report-format-card">
            <Icon size={28} color="var(--accent)" />
            <h3>{label}</h3>
            <p className="text-muted">{desc}</p>
            <button type="button" className="btn btn--primary" onClick={() => download(id)}>
              <Download size={14} /> Download
            </button>
          </article>
        ))}
      </section>
    </>
  );
}
