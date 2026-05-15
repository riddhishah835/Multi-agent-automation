import { Bell, Moon, Search, Sun, User } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { tenants } from '../../data/mockData';

export default function TopNav({ onMenuClick }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="top-nav">
      <button type="button" className="icon-btn" onClick={onMenuClick} aria-label="Menu">
        <span className="brand__logo">A</span>
      </button>
      <div className="brand">
        <span>Advanced AI Agentic OS</span>
      </div>

      <label className="top-nav__search">
        <Search size={16} />
        <input type="search" placeholder="Search workflows, agents, traces…" />
      </label>

      <div className="top-nav__actions">
        <select className="select-pill" defaultValue={tenants[0]} aria-label="Tenant router">
          {tenants.map((t) => (
            <option key={t} value={t}>
              Tenant: {t}
            </option>
          ))}
        </select>
        <button type="button" className="icon-btn" aria-label="Search">
          <Search size={18} />
        </button>
        <button type="button" className="icon-btn icon-btn--badge" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <button type="button" className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button type="button" className="icon-btn" aria-label="Profile">
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
