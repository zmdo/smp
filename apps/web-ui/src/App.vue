<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";
import { useAuth } from "./stores/auth";

const route = useRoute();
const auth = useAuth();

async function logout() {
  await auth.logout();
  window.location.assign("/login");
}
</script>

<template>
  <RouterView v-if="route.name === 'login'" />
  <div v-else class="app">
    <aside class="sider">
      <div class="logo">
        <span class="logo-mark">策</span>
        <span>策略控制台</span>
      </div>
      <nav class="nav">
        <RouterLink to="/servers" class="nav-item" :class="{ 'is-on': route.path.startsWith('/servers') }">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <rect x="1.5" y="2.5" width="13" height="4" rx="1" stroke="currentColor" />
            <rect x="1.5" y="9.5" width="13" height="4" rx="1" stroke="currentColor" />
            <circle cx="4" cy="4.5" r="0.7" fill="currentColor" />
            <circle cx="4" cy="11.5" r="0.7" fill="currentColor" />
          </svg>
          服务器
        </RouterLink>
      </nav>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <nav class="tabs">
          <RouterLink to="/servers" class="tab" :class="{ 'is-on': route.path.startsWith('/servers') }">服务器</RouterLink>
        </nav>
        <div class="top-actions">
          <button class="link" type="button" @click="logout">退出</button>
        </div>
      </header>
      <div class="content">
        <p v-if="auth.passwordIsDefault" class="banner">
          当前仍是默认口令 changeme。正式接入服务器前，请修改 ADMIN_PASSWORD 并重启网站。
        </p>
        <RouterView />
      </div>
    </div>
  </div>
</template>
