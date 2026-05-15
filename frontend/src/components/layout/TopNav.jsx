import { useNavigate } from 'react-router-dom';
import { Bell, LogOut, Moon, Search, Shield, Sun, User } from 'lucide-react';
import GlobalSearch from '../common/GlobalSearch';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';

export default function TopNav({ onMenuClick }) {
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="top-nav">
      <button type="button" className="icon-btn" onClick={onMenuClick} aria-label="Menu">
        <span className="brand__logo">
          <Shield size={16} />
        </span>
      </button>
      <section className="brand">
        <span className="brand__title">Vendor Compliance OS</span>
        <span className="brand__tag">Tenant: {user?.tenantId || '—'}</span>
      </section>

      <GlobalSearch />

      <section className="top-nav__actions">
        <section className="user-menu">
          <span className="icon-btn" aria-hidden>
            <User size={18} />
          </span>
          <span className="user-menu__info">
            <span className="user-menu__name">{user?.name}</span>
            <span className="user-menu__role">{user?.role}</span>
          </span>
        </section>
        <button type="button" className="icon-btn icon-btn--badge" aria-label="Alerts">
          <Bell size={18} />
        </button>
        <button type="button" className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button type="button" className="icon-btn" onClick={handleLogout} aria-label="Sign out" title="Sign out">
          <LogOut size={18} />
        </button>
      </section>
    </header>
  );
}
