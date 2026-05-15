import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Overview from './pages/Overview';
import AgentGenerator from './pages/AgentGenerator';
import WorkflowHitl from './pages/WorkflowHitl';
import Observability from './pages/Observability';
import ToolsPage from './pages/ToolsPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Overview />} />
        <Route path="dashboard" element={<Overview />} />
        <Route path="agents" element={<AgentGenerator />} />
        <Route path="workflows" element={<WorkflowHitl />} />
        <Route path="tools" element={<ToolsPage />} />
        <Route path="observability" element={<Observability />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
