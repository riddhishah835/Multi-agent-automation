import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Lock, Mail, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { DEMO_USERS } from '../config/authConfig';

export default function Login() {
  const { login, isAuthenticated, loading } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const from = location.state?.from || '/';

  if (!loading && isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    const result = await login(email, password);
    setSubmitting(false);

    if (result.ok) {
      addToast(
        result.apiConnected
          ? 'Signed in — API connected'
          : 'Signed in (offline demo mode)',
        'success'
      );
      navigate(from, { replace: true });
    } else {
      setError(result.error || 'Login failed');
    }
  };

  const fillDemo = (user) => {
    setEmail(user.email);
    setPassword(user.password);
  };

  return (
    <section className="login-page">
      <article className="login-card">
        <header className="login-card__header">
          <span className="brand__logo login-card__logo">
            <Shield size={28} />
          </span>
          <h1>Vendor Compliance OS</h1>
          <p>Sign in to your compliance workspace</p>
        </header>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && <p className="login-form__error" role="alert">{error}</p>}

          <label className="login-field">
            <Mail size={16} />
            <input
              type="email"
              placeholder="Work email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>

          <label className="login-field">
            <Lock size={16} />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button type="submit" className="btn btn--primary login-form__submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <section className="login-demo">
          <p className="login-demo__title">Demo accounts</p>
          <ul>
            {DEMO_USERS.map((u) => (
              <li key={u.email}>
                <button type="button" className="login-demo__btn" onClick={() => fillDemo(u)}>
                  <strong>{u.role}</strong>
                  <span>{u.email}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </article>
    </section>
  );
}
