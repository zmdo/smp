import { defineStore } from "pinia";
import { api } from "../api";

export const useAuth = defineStore("auth", {
  state: () => ({
    checked: false,
    authenticated: false,
    passwordIsDefault: false,
  }),
  actions: {
    async refresh() {
      try {
        const me = await api<{ authenticated: boolean; password_is_default: boolean }>("/api/auth/me");
        this.authenticated = me.authenticated;
        this.passwordIsDefault = me.password_is_default;
      } catch {
        this.authenticated = false;
        this.passwordIsDefault = false;
      } finally {
        this.checked = true;
      }
    },
    async login(password: string) {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) });
      await this.refresh();
    },
    async logout() {
      await api("/api/auth/logout", { method: "POST" });
      this.authenticated = false;
    },
  },
});
