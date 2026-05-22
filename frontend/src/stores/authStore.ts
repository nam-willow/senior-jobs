import { create } from 'zustand';
import { api } from '../lib/api';

interface UserInfo {
  user_id: string;
  name: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
}

interface AuthState {
  isLoggedIn: boolean;
  userInfo: UserInfo | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  init: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoggedIn: !!localStorage.getItem('access_token'),
  userInfo: null,

  init() {
    set({ isLoggedIn: !!localStorage.getItem('access_token') });
  },

  async fetchMe() {
    try {
      const r = await api.get('/auth/me');
      set({ userInfo: r.data });
    } catch {
      // ignore — userInfo stays null
    }
  },

  async login(email, password) {
    const r = await api.post('/auth/login', { email, password });
    localStorage.setItem('access_token', r.data.access_token);
    localStorage.setItem('refresh_token', r.data.refresh_token);
    set({ isLoggedIn: true });
    // fetch user info after login
    try {
      const me = await api.get('/auth/me');
      set({ userInfo: me.data });
    } catch { /* ignore */ }
  },

  async logout() {
    const refresh = localStorage.getItem('refresh_token');
    if (refresh) {
      try { await api.post('/auth/logout', { refresh_token: refresh }); } catch { /* ignore */ }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ isLoggedIn: false, userInfo: null });
  },
}));
