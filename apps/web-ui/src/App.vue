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
        <RouterLink to="/servers" class="nav-item" :class="{ 'is-on': route.path.startsWith('/servers') || route.path.startsWith('/keys') }">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <rect x="1.5" y="2.5" width="13" height="4" rx="1" stroke="currentColor" />
            <rect x="1.5" y="9.5" width="13" height="4" rx="1" stroke="currentColor" />
            <circle cx="4" cy="4.5" r="0.7" fill="currentColor" />
            <circle cx="4" cy="11.5" r="0.7" fill="currentColor" />
          </svg>
          服务器
        </RouterLink>
        <RouterLink to="/account" class="nav-item" :class="{ 'is-on': route.path.startsWith('/account') }">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <circle cx="8" cy="5.5" r="2.2" stroke="currentColor" />
            <path d="M3.2 13.2c.8-2.2 2.5-3.2 4.8-3.2s4 1 4.8 3.2" stroke="currentColor" stroke-linecap="round" />
          </svg>
          账户
        </RouterLink>
      </nav>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <nav v-if="route.path.startsWith('/account')" class="tabs">
          <RouterLink to="/account" class="tab" :class="{ 'is-on': route.path.startsWith('/account') }">登录安全</RouterLink>
        </nav>
        <nav v-else class="tabs">
          <RouterLink to="/servers" class="tab" :class="{ 'is-on': route.path.startsWith('/servers') }">服务器实例</RouterLink>
          <RouterLink to="/keys" class="tab" :class="{ 'is-on': route.path.startsWith('/keys') }">服务器密钥</RouterLink>
        </nav>
        <div class="top-actions">
          <button class="link" type="button" @click="logout">退出</button>
        </div>
      </header>
      <div class="content">
        <p v-if="auth.passwordIsDefault" class="banner">
          当前仍是默认账户 admin、密码 changeme。请到「账户 / 登录安全」里修改密码。
        </p>
        <RouterView />
      </div>
    </div>
  </div>
</template>
