import { NavLink } from 'react-router-dom';
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Download,
  FileUp,
  GitBranch,
  History,
  Home,
  Search,
  Settings,
  Shield,
  UserCheck,
} from 'lucide-react';
import LiveLogSidebar from '../common/LiveLogSidebar';

const mainNav = [
  { to: '/', label: 'Audit Queue', icon: Home, end: true },
  { to: '/upload', label: 'Upload Docs', icon: FileUp },
  { to: '/pipeline', label: 'Audit Pipeline', icon: GitBranch },
  { to: '/findings', label: 'Findings', icon: ClipboardList },
  { to: '/evidence', label: 'Evidence', icon: Search },
  { to: '/review', label: 'Human Review', icon: UserCheck },
  { to: '/reports', label: 'Reports', icon: Download },
  { to: '/history', label: 'Audit History', icon: History },
];

const adminNav = [
  { to: '/observability', label: 'System Health', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ collapsed, onToggle, mobileOpen }) {
  const cls = ['sidebar', collapsed && 'sidebar--collapsed', mobileOpen && 'sidebar--open']
    .filter(Boolean)
    .join(' ');

  return (
    <aside className={cls}>
      <button
        type="button"
        className="icon-btn sidebar__toggle"
        onClick={onToggle}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>

      <section className="sidebar__scroll">
        <p className="sidebar__section-label">
          <Shield size={14} /> Compliance
        </p>
        <nav>
          {mainNav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <p className="sidebar__section-label sidebar__section-label--admin">Admin</p>
        <nav>
          {adminNav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item${isActive ? ' nav-item--active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </section>

      <LiveLogSidebar collapsed={collapsed} />
    </aside>
  );
}
