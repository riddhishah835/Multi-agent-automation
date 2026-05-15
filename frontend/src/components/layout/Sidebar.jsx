import { NavLink } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  GitBranch,
  LayoutGrid,
  Network,
  Wrench,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/agents', label: 'Agents', icon: Network },
  { to: '/workflows', label: 'Workflows', icon: GitBranch },
  { to: '/tools', label: 'Tools', icon: Wrench },
  { to: '/observability', label: 'Observability', icon: Eye },
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
      <nav>
        {navItems.map(({ to, label, icon: Icon, end }) => (
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
    </aside>
  );
}
