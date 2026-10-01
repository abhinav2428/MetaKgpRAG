import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { User } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  signin: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name?: string) => Promise<void>;
  signout: () => void;
  setTokenFromCallback: (token: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: restore token from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('gm_token');
    if (stored) {
      setToken(stored);
      api.me()
        .then(setUser)
        .catch(() => { localStorage.removeItem('gm_token'); })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const _storeToken = useCallback(async (t: string) => {
    localStorage.setItem('gm_token', t);
    setToken(t);
    const me = await api.me();
    setUser(me);
  }, []);

  const signin = useCallback(async (email: string, password: string) => {
    const res = await api.signin(email, password);
    await _storeToken(res.access_token);
  }, [_storeToken]);

  const signup = useCallback(async (email: string, password: string, name?: string) => {
    const res = await api.signup(email, password, name);
    await _storeToken(res.access_token);
  }, [_storeToken]);

  const signout = useCallback(() => {
    localStorage.removeItem('gm_token');
    setToken(null);
    setUser(null);
  }, []);

  const setTokenFromCallback = useCallback(async (t: string) => {
    await _storeToken(t);
  }, [_storeToken]);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, signin, signup, signout, setTokenFromCallback }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
