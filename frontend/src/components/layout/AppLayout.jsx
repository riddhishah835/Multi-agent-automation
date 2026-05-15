import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import TopNav from './TopNav';
import Sidebar from './Sidebar';
import LiveLogPanel from '../common/LiveLogPanel';

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <TopNav onMenuClick={() => setMobileOpen((o) => !o)} />
      <div className="app-body">
        <Sidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed((c) => !c)}
          mobileOpen={mobileOpen}
        />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
      <LiveLogPanel />
    </div>
  );
}
