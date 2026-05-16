import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './pages/Login';
import AuditQueue from './pages/AuditQueue';
import DocumentUpload from './pages/DocumentUpload';
import AuditPipeline from './pages/AuditPipeline';
import EvidenceViewer from './pages/EvidenceViewer';
import Findings from './pages/Findings';
import HumanReview from './pages/HumanReview';
import Reports from './pages/Reports';
import AuditHistory from './pages/AuditHistory';
import Observability from './pages/Observability';
import TenantSettings from './pages/TenantSettings';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AuditQueue />} />
        <Route path="dashboard" element={<AuditQueue />} />
        <Route path="upload" element={<DocumentUpload />} />
        <Route path="pipeline" element={<AuditPipeline />} />
        <Route path="findings" element={<Findings />} />
        <Route path="evidence" element={<EvidenceViewer />} />
        <Route path="review" element={<HumanReview />} />
        <Route path="reports" element={<Reports />} />
        <Route path="history" element={<AuditHistory />} />
        <Route path="observability" element={<Observability />} />
        <Route path="settings" element={<TenantSettings />} />
        <Route path="agents" element={<Navigate to="/settings" replace />} />
        <Route path="workflows" element={<Navigate to="/review" replace />} />
        <Route path="tools" element={<Navigate to="/upload" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
