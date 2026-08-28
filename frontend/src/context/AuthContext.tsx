import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  getMe, login as apiLogin, loginWithGitHub as apiLoginWithGitHub,
  loginWithGoogle as apiLoginWithGoogle, loginWithMicrosoft as apiLoginWithMicrosoft,
  logout as apiLogout,
} from "../api/endpoints";
import { tokenStorage } from "../api/client";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, otpCode?: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  loginWithMicrosoft: (idToken: string) => Promise<void>;
  loginWithGitHub: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    if (!tokenStorage.getAccess()) {
      setUser(null);
      return;
    }
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string, otpCode?: string) {
    await apiLogin(email, password, otpCode);
    await refreshUser();
  }

  async function loginWithGoogle(idToken: string) {
    await apiLoginWithGoogle(idToken);
    await refreshUser();
  }

  async function loginWithMicrosoft(idToken: string) {
    await apiLoginWithMicrosoft(idToken);
    await refreshUser();
  }

  async function loginWithGitHub(code: string) {
    await apiLoginWithGitHub(code);
    await refreshUser();
  }

  async function logout() {
    await apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, loginWithMicrosoft, loginWithGitHub, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
