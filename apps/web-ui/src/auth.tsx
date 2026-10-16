import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";

export interface Me {
  authenticated: boolean;
  username: string | null;
  password_is_default: boolean;
  totp_enabled: boolean;
}

export interface LoginResult {
  ok: boolean;
  totp_required: boolean;
}

interface AuthState {
  checked: boolean;
  authenticated: boolean;
  username: string | null;
  passwordIsDefault: boolean;
  totpEnabled: boolean;
  refresh: () => Promise<void>;
  login: (username: string, password: string, totpCode?: string) => Promise<LoginResult>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [checked, setChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [passwordIsDefault, setPasswordIsDefault] = useState(false);
  const [totpEnabled, setTotpEnabled] = useState(false);

  async function refresh() {
    try {
      const me = await api<Me>("/api/auth/me");
      setAuthenticated(me.authenticated);
      setUsername(me.username);
      setPasswordIsDefault(me.password_is_default);
      setTotpEnabled(me.totp_enabled);
    } catch {
      setAuthenticated(false);
      setUsername(null);
      setPasswordIsDefault(false);
      setTotpEnabled(false);
    } finally {
      setChecked(true);
    }
  }

  async function login(name: string, password: string, totpCode?: string) {
    const body: Record<string, string> = { username: name, password };
    if (totpCode) body.totp_code = totpCode;
    const result = await api<LoginResult>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (result.ok) await refresh();
    return result;
  }

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    setAuthenticated(false);
    setUsername(null);
    setTotpEnabled(false);
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <AuthContext.Provider value={{ checked, authenticated, username, passwordIsDefault, totpEnabled, refresh, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("auth missing");
  return value;
}
