import { create } from 'zustand';
import type { PageType, TabType } from '../types';

interface AppState {
  page: PageType;
  tab: TabType;
  year: number;
  month: number;
  selectedSenior: number | null;
  focusSenior: number | null;
  set: (key: keyof Omit<AppState, 'set'>, value: AppState[keyof Omit<AppState, 'set'>]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  page: 'dashboard',
  tab: '공익활동형',
  year: 2026,
  month: 5,
  selectedSenior: null,
  focusSenior: null,
  set: (key, value) => set({ [key]: value } as Partial<AppState>),
}));
