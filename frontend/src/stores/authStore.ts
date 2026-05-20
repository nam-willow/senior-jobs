import { create } from 'zustand';
import { api } from '../lib/api';

interface AuthState {
  isLoggedIn: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  init: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoggedIn: !!localStorage.getItem('access_token'),

  init() {
    set({ isLoggedIn: !!localStorage.getItem('access_token') });
  },

  async login(email, password) {
    const r = await api.post('/auth/login', { email, password });
    localStorage.setItem('access_token', r.data.access_token);
    localStorage.setItem('refresh_token', r.data.refresh_token);
    set({ isLoggedIn: true });
  },

  async logout() {
    const refresh = localStorage.getItem('refresh_token');
    if (refresh) {
      try { await api.post('/auth/logout', { refresh_token: refresh }); } catch { /* ignore */ }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ isLoggedIn: false });
  },
}));
