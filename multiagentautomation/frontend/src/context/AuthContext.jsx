import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  AUTH_STORAGE_KEY,
  DEMO_USERS,
  buildBearerToken,
} from '../config/authConfig';
import { checkApiHealth } from '../utils/api';

const AuthContext = createContext(null);

function loadSession() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSession(session) {
  if (session) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const session = loadSession();
    if (session?.token && session?.user) {
      setUser(session.user);
      setToken(session.token);
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    const normalized = email.trim().toLowerCase();
    const match = DEMO_USERS.find(
      (u) => u.email.toLowerCase() === normalized && u.password === password
    );

    if (!match) {
      return { ok: false, error: 'Invalid email or password' };
    }

    const bearerToken = buildBearerToken(match.tenantId);
    const sessionUser = {
      email: match.email,
      name: match.name,
      role: match.role,
      tenantId: match.tenantId,
    };

    const apiOk = await checkApiHealth();

    const session = {
      user: sessionUser,
      token: bearerToken,
      loginAt: new Date().toISOString(),
    };

    saveSession(session);
    setUser(sessionUser);
    setToken(bearerToken);

    return {
      ok: true,
      apiConnected: apiOk,
    };
  }, []);

  const logout = useCallback(() => {
    saveSession(null);
    setUser(null);
    setToken(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(user && token),
      loading,
      login,
      logout,
    }),
    [user, token, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
