const API_BASE = '';
export const USE_BACKEND = true; // Toggle for real backend vs mock

const getAuthHeaders = () => ({
  'Authorization': 'Bearer tenant_acme_v1',
  'Content-Type': 'application/json'
});

export async function startAudit(file, tenantId = 'acme') {
  if (!USE_BACKEND) {
    return { audit_id: `mock-audit-${Date.now()}`, status: 'running' };
  }

  const payload = {
    task: `Process audit for document: ${file.name}`,
    workflow_id: 'default',
    priority: 1,
    metadata: { source: 'dashboard', filename: file.name, tenant: tenantId }
  };

  try {
    const response = await fetch(`${API_BASE}/api/submit`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    return { audit_id: data.run_id, status: data.status };
  } catch (error) {
    console.error('Failed to start audit:', error);
    throw error;
  }
}

export async function getAuditState(auditId) {
  if (!USE_BACKEND) {
    return { status: 'running', current_node: 'OCR Processing', risk_score: 45, findings: [], vendor_name: 'Mock Vendor' };
  }

  try {
    const response = await fetch(`${API_BASE}/api/status/${auditId}`, { headers: getAuthHeaders() });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    
    // Map backend status to UI expected status
    let uiStatus = data.status;
    if (data.status === 'waiting_approval') uiStatus = 'hitl_paused';
    
    return {
      status: uiStatus,
      current_node: data.message || 'Processing...',
      risk_score: data.result?.risk_score || 45,
      findings: data.result?.findings || [],
      vendor_name: data.result?.vendor_name || 'SecureHost Inc'
    };
  } catch (error) {
    console.error(`Failed to get state for ${auditId}:`, error);
    throw error;
  }
}

export async function getHistory() {
  if (!USE_BACKEND) {
    return null; // Let the UI fallback to mock data if no backend
  }

  try {
    const response = await fetch(`${API_BASE}/api/history`, { headers: getAuthHeaders() });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to get history:', error);
    throw error;
  }
}

export async function sendHITLDecision(auditId, decision) {
  if (!USE_BACKEND) {
    return { status: 'success', decision };
  }

  const payload = {
    approved: decision === 'approved',
    reason: `HITL Decision: ${decision}`,
    approver_id: 'analyst_ui'
  };

  try {
    const response = await fetch(`${API_BASE}/api/approve/${auditId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error(`Failed to send decision for ${auditId}:`, error);
    throw error;
  }
}

export async function getAuditReport(auditId) {
  return { content: '# Final Report\n\nGenerated automatically.' };
}

export async function getAuditLogs(auditId) {
  return [{ timestamp: new Date().toISOString(), message: 'Log entry' }];
}
