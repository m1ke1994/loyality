import { defineStore } from "pinia";

type User = {
  id: number;
  email: string;
  phone: string;
  phone_verified: boolean;
  email_verified: boolean;
  role: string;
};

type Tokens = {
  access: string;
  refresh: string;
};

type AuthState = {
  user: User | null;
  tokens: Tokens | null;
  tenant: string | null;
};

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    tokens: null,
    tenant: null,
  }),
  actions: {
    setAuth(payload: { user: User; tokens: Tokens; tenant: string }) {
      this.user = payload.user;
      this.tokens = payload.tokens;
      this.tenant = payload.tenant;
      localStorage.setItem("auth", JSON.stringify(payload));
    },
    updateTokens(tokens: Tokens) {
      this.tokens = tokens;
      const raw = localStorage.getItem("auth");
      const stored = raw ? JSON.parse(raw) : {};
      const payload = {
        user: this.user ?? stored.user ?? null,
        tokens,
        tenant: this.tenant ?? stored.tenant ?? null,
      };
      localStorage.setItem("auth", JSON.stringify(payload));
    },
    load() {
      const raw = localStorage.getItem("auth");
      if (raw) {
        const parsed = JSON.parse(raw);
        this.user = parsed.user;
        this.tokens = parsed.tokens;
        this.tenant = parsed.tenant;
      }
    },
    logout() {
      this.user = null;
      this.tokens = null;
      this.tenant = null;
      localStorage.removeItem("auth");
    },
  },
});
