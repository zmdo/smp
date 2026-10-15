import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "./stores/auth";
import AccountView from "./views/AccountView.vue";
import CardAccountView from "./views/CardAccountView.vue";
import CryptoAccountView from "./views/CryptoAccountView.vue";
import KeyListView from "./views/KeyListView.vue";
import LoginView from "./views/LoginView.vue";
import ServerDetailView from "./views/ServerDetailView.vue";
import ServerFormView from "./views/ServerFormView.vue";
import ServerListView from "./views/ServerListView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/", redirect: "/servers" },
    { path: "/servers", name: "servers", component: ServerListView },
    { path: "/servers/new", name: "server-new", component: ServerFormView },
    { path: "/servers/:id/edit", name: "server-edit", component: ServerFormView },
    { path: "/servers/:id", name: "server-detail", component: ServerDetailView },
    { path: "/keys", name: "keys", component: KeyListView },
    { path: "/account", redirect: "/settings" },
    { path: "/settings", name: "settings", component: AccountView },
    { path: "/accounts/crypto", name: "crypto-accounts", component: CryptoAccountView },
    { path: "/accounts/cards", name: "card-accounts", component: CardAccountView },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuth();
  if (!auth.checked) {
    try {
      await auth.refresh();
    } catch {
      auth.checked = true;
      auth.authenticated = false;
    }
  }
  if (to.meta.public) {
    if (auth.authenticated && to.name === "login") return { name: "servers" };
    return true;
  }
  if (!auth.authenticated) return { name: "login", query: { next: to.fullPath } };
  return true;
});
