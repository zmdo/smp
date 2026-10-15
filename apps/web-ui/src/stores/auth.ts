import { defineStore } from "pinia";
import { api } from "../api";

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

export const useAuth = defineStore("auth", {
  state: () => ({
    checked: false,
    authenticated: false,
    username: "" as string | null,
    passwordIsDefault: false,
    totpEnabled: false,
  }),
  actions: {
    async refresh() {
      try {
        const me = await api<Me>("/api/auth/me");
        this.authenticated = me.authenticated;
        this.username = me.username;
        this.passwordIsDefault = me.password_is_default;
        this.totpEnabled = me.totp_enabled;
      } catch {
        this.authenticated = false;
        this.username = null;
        this.passwordIsDefault = false;
        this.totpEnabled = false;
      } finally {
        this.checked = true;
      }
    },
    async login(username: string, password: string, totpCode?: string) {
      const body: Record<string, string> = { username, password };
      if (totpCode) body.totp_code = totpCode;
      const result = await api<LoginResult>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (result.ok) await this.refresh();
      return result;
    },
    async logout() {
      await api("/api/auth/logout", { method: "POST" });
      this.authenticated = false;
      this.username = null;
      this.totpEnabled = false;
    },
  },
});
