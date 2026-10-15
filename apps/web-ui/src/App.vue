<script setup lang="ts">
import { ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { useAuth } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuth();
const accountsOpen = ref(true);

watch(
  () => route.path,
  (path) => {
    if (path.startsWith("/accounts")) accountsOpen.value = true;
  },
  { immediate: true },
);

function toggleAccounts() {
  if (!route.path.startsWith("/accounts")) {
    accountsOpen.value = true;
    void router.push("/accounts/crypto");
    return;
  }
  accountsOpen.value = !accountsOpen.value;
}

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
        <div class="nav-group" :class="{ 'is-open': accountsOpen }">
          <button class="nav-item" type="button" @click="toggleAccounts">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1.6" y="3.4" width="12.8" height="9.2" rx="1.4" stroke="currentColor" />
              <path d="M1.6 6.4h12.8" stroke="currentColor" />
            </svg>
            资金账户
            <svg class="nav-caret" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M4.2 2.4 7.8 6 4.2 9.6" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <div v-show="accountsOpen" class="nav-sub">
            <RouterLink to="/accounts/crypto" class="nav-sub-item" :class="{ 'is-on': route.path.startsWith('/accounts/crypto') }">数字钱包</RouterLink>
            <RouterLink to="/accounts/cards" class="nav-sub-item" :class="{ 'is-on': route.path.startsWith('/accounts/cards') }">信用卡</RouterLink>
          </div>
        </div>
        <RouterLink to="/servers" class="nav-item" :class="{ 'is-on': route.path.startsWith('/servers') || route.path.startsWith('/keys') }">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <rect x="1.5" y="2.5" width="13" height="4" rx="1" stroke="currentColor" />
            <rect x="1.5" y="9.5" width="13" height="4" rx="1" stroke="currentColor" />
            <circle cx="4" cy="4.5" r="0.7" fill="currentColor" />
            <circle cx="4" cy="11.5" r="0.7" fill="currentColor" />
          </svg>
          服务器
        </RouterLink>
      </nav>
      <div class="nav-foot">
        <RouterLink to="/settings" class="nav-item" :class="{ 'is-on': route.path.startsWith('/settings') }">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <circle cx="8" cy="8" r="2" stroke="currentColor" />
            <path
              d="M8 1.6v1.8M8 12.6v1.8M1.6 8h1.8M12.6 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3"
              stroke="currentColor"
              stroke-linecap="round"
            />
          </svg>
          平台设置
        </RouterLink>
      </div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <nav v-if="route.path.startsWith('/settings')" class="tabs">
          <RouterLink to="/settings" class="tab" :class="{ 'is-on': route.path.startsWith('/settings') }">登录安全</RouterLink>
        </nav>
        <nav v-else-if="route.path.startsWith('/accounts/crypto')" class="tabs">
          <RouterLink to="/accounts/crypto" class="tab is-on">钱包实例</RouterLink>
        </nav>
        <nav v-else-if="route.path.startsWith('/accounts/cards')" class="tabs">
          <RouterLink to="/accounts/cards" class="tab is-on">虚拟信用卡</RouterLink>
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
          当前仍是默认用户名 admin、密码 changeme。请到「平台设置 / 登录安全」里修改。
        </p>
        <RouterView />
      </div>
    </div>
  </div>
</template>
