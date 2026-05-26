import { create } from 'zustand';

interface User {
  id: string;
  email: string;
  is_verified: boolean;
  created_at: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  sessionId: string | null;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  generateNewSession: () => void;
}

const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export const useAuth = create<AuthState>((set) => ({
  // Read token from fallback memory to support cross-domain deployments (bypassing third-party cookie blocks)
  token: typeof window !== "undefined" ? (localStorage.getItem("access_token_mem") || null) : null,
  user: null,
  sessionId: typeof window !== "undefined" ? localStorage.getItem("session_id") : null,
  setToken: (token) => {
    if (typeof window !== "undefined") {
      const newSession = generateUUID();
      localStorage.setItem("session_id", newSession);
      localStorage.setItem("access_token_mem", token);
      set({ token: token, sessionId: newSession });
    } else {
      set({ token: token });
    }
  },
  setUser: (user) => set({ user }),
  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("session_id");
      localStorage.removeItem("access_token_mem");
    }
    set({ token: null, user: null, sessionId: null });
  },
  generateNewSession: () => {
    if (typeof window !== "undefined") {
      const newSession = generateUUID();
      localStorage.setItem("session_id", newSession);
      set({ sessionId: newSession });
    }
  }
}));

