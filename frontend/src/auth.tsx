import { createContext, useContext, useMemo, useState } from "react";

import { api } from "./api";

type AuthUser = {
  id: string;
  email: string;
};

type AuthResponse = {
  token: string;
  user: AuthUser;
};

type AuthContextType = {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function parseToken(token: string): { exp?: number } | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return null;
    }
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as { exp?: number };
  } catch {
    return null;
  }
}

function isTokenValid(token: string | null): boolean {
  if (!token) {
    return false;
  }
  const payload = parseToken(token);
  if (!payload?.exp) {
    return true;
  }
  return payload.exp * 1000 > Date.now();
}

function loadInitialAuth(): { token: string | null; user: AuthUser | null } {
  const token = localStorage.getItem("aiops_token");
  const userRaw = localStorage.getItem("aiops_user");
  if (!isTokenValid(token)) {
    localStorage.removeItem("aiops_token");
    localStorage.removeItem("aiops_user");
    return { token: null, user: null };
  }

  if (!userRaw) {
    return { token, user: null };
  }

  try {
    return {
      token,
      user: JSON.parse(userRaw) as AuthUser,
    };
  } catch {
    localStorage.removeItem("aiops_user");
    return { token, user: null };
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const initial = loadInitialAuth();
  const [token, setToken] = useState<string | null>(initial.token);
  const [user, setUser] = useState<AuthUser | null>(initial.user);

  const storeSession = (auth: AuthResponse) => {
    setToken(auth.token);
    setUser(auth.user);
    localStorage.setItem("aiops_token", auth.token);
    localStorage.setItem("aiops_user", JSON.stringify(auth.user));
  };

  const login = async (email: string, password: string) => {
    const response = await api.post<AuthResponse>("/api/auth/login", { email, password });
    storeSession(response.data);
  };

  const signup = async (email: string, password: string) => {
    const response = await api.post<AuthResponse>("/api/auth/signup", { email, password });
    storeSession(response.data);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("aiops_token");
    localStorage.removeItem("aiops_user");
  };

  const value = useMemo<AuthContextType>(
    () => ({
      token,
      user,
      isAuthenticated: isTokenValid(token),
      login,
      signup,
      logout,
    }),
    [token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
