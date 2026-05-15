import { useState, useEffect } from 'react';
import PageHeader from '../components/common/PageHeader';
import PipelineTimeline from '../components/common/PipelineTimeline';
import RiskScorePanel from '../components/common/RiskScorePanel';
import { pipelineSteps } from '../data/mockData';
import { getAuditState } from '../api/client';
import { useToast } from '../context/ToastContext';

export default function AuditPipeline() {
  const { addToast } = useToast();
  const [realTimeState, setRealTimeState] = useState(null);

  useEffect(() => {
    const auditId = localStorage.getItem('current_audit_id');
    if (!auditId) return;
    let errorToastShown = false;

    const fetchState = async () => {
      try {
        const state = await getAuditState(auditId);
        if (state) setRealTimeState(state);
      } catch (err) {
        if (!errorToastShown) {
          addToast('Backend disconnected - using demo mode', 'error');
          errorToastShown = true;
        }
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 2000);
    return () => clearInterval(interval);
  }, [addToast]);

  const displayAuditId = localStorage.getItem('current_audit_id') || 'No Audit Started';
  const displayVendor = realTimeState?.vendor_name || 'Loading Vendor...';
  const displayRiskScore = realTimeState?.risk_score !== undefined 
    ? { 
        overall: realTimeState.risk_score, 
        compliance: Math.max(0, 100 - realTimeState.risk_score), 
        recommendation: realTimeState.risk_score > 70 ? 'Reject (High Risk)' : 'Approve (Low Risk)'
      } 
    : { overall: 0, compliance: 100, recommendation: 'Pending' };
  const displayCurrentNode = realTimeState?.current_node || 'Waiting for State...';

  const workflowNodes = [
    { id: 'start', name: 'Initialization' },
    { id: 'ingestion', name: 'Document Ingestion' },
    { id: 'document_classification', name: 'Classification & Routing' },
    { id: 'rule_retrieval', name: 'Rule Retrieval' },
    { id: 'adversarial_audit', name: 'Adversarial Audit' },
    { id: 'gap_analysis', name: 'Gap Analysis' },
    { id: 'report_generation', name: 'Report Generation' },
    { id: 'human_review_gate', name: 'Human Review Gate' }
  ];

  const getCurrentStepIndex = () => {
    if (!realTimeState) return 0;
    if (realTimeState.status === 'completed' || realTimeState.status === 'approved') return workflowNodes.length;
    const index = workflowNodes.findIndex(n => n.id === realTimeState.current_node);
    return index >= 0 ? index : 0;
  };

  const currentStepIndex = getCurrentStepIndex();

  const dynamicSteps = workflowNodes.map((node, index) => {
    let status = 'pending';
    if (index < currentStepIndex) status = 'complete';
    else if (index === currentStepIndex) {
      if (realTimeState?.status === 'hitl_paused' || realTimeState?.status === 'waiting_approval') {
        status = 'paused';
      } else {
        status = 'running';
      }
    }
    return { ...node, status };
  });

  return (
    <>
      <PageHeader
        title="Audit Pipeline"
        subtitle={`Workflow progress — ${displayVendor} (${displayAuditId})`}
        actions={
          <select className="select-pill" value={displayAuditId} onChange={() => {}}>
            <option value={displayAuditId}>{displayAuditId} — {displayVendor}</option>
            <option>AUD-2398 — SecureHost Inc</option>
          </select>
        }
      />

      <section className="pipeline-layout">
        <article className="card pipeline-card">
          <h2 className="card__title">Node-by-node progress</h2>
          <p className="text-muted" style={{ marginBottom: '1.25rem' }}>
            Frameworks: SOC2, ISO 27001
          </p>
          <PipelineTimeline steps={dynamicSteps} />
          <section className="pipeline-legend">
            <span><span className="dot dot--done" /> Complete</span>
            <span><span className="dot dot--pause" /> Waiting approval</span>
            <span><span className="dot dot--pending" /> Pending</span>
          </section>
        </article>

        <aside>
          <RiskScorePanel data={displayRiskScore} />
          <article className="card" style={{ marginTop: '1rem' }}>
            <h2 className="card__title">Current step</h2>
            <p className="pipeline-current">{displayCurrentNode}</p>
            <p className="text-muted">
              {realTimeState?.status === 'hitl_paused' ? 'Analyst review required before continuing.' : 'Processing current audit stage.'}
            </p>
          </article>
        </aside>
      </section>
    </>
  );
}
