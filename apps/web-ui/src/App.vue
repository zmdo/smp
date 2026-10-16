<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { useAuth } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuth();
const openGroup = ref<string | null>(null);

function toggleGroup(name: string, path: string) {
  if (openGroup.value === name) {
    openGroup.value = null;
    return;
  }
  openGroup.value = name;
  if (!route.path.startsWith(path)) void router.push(path);
}

function closeGroups() {
  openGroup.value = null;
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
        <p class="nav-title">概览</p>
        <RouterLink to="/dashboard" class="nav-item" :class="{ 'is-on': route.path.startsWith('/dashboard') }" @click="closeGroups">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <rect x="1.6" y="1.6" width="5.2" height="5.2" rx="1" stroke="currentColor" />
            <rect x="9.2" y="1.6" width="5.2" height="5.2" rx="1" stroke="currentColor" />
            <rect x="1.6" y="9.2" width="5.2" height="5.2" rx="1" stroke="currentColor" />
            <rect x="9.2" y="9.2" width="5.2" height="5.2" rx="1" stroke="currentColor" />
          </svg>
          仪表盘
        </RouterLink>
        <p class="nav-title">运营</p>
        <div class="nav-group" :class="{ 'is-open': openGroup === 'quant' }">
          <button class="nav-item" type="button" @click="toggleGroup('quant', '/quant')">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M1.8 11.5 5.6 7.6l2.3 2.2 5.3-6" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M9.6 3.8h3.6V7.4" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            量化交易
            <svg class="nav-caret" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M4.2 2.4 7.8 6 4.2 9.6" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <div v-show="openGroup === 'quant'" class="nav-sub">
            <RouterLink to="/quant/crypto" class="nav-sub-item" :class="{ 'is-on': route.path.startsWith('/quant/crypto') }">数字货币</RouterLink>
          </div>
        </div>
        <p class="nav-title">资源</p>
        <div class="nav-group" :class="{ 'is-open': openGroup === 'accounts' }">
          <button class="nav-item" type="button" @click="toggleGroup('accounts', '/accounts')">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1.6" y="3.4" width="12.8" height="9.2" rx="1.4" stroke="currentColor" />
              <path d="M1.6 6.4h12.8" stroke="currentColor" />
            </svg>
            资金账户
            <svg class="nav-caret" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="M4.2 2.4 7.8 6 4.2 9.6" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <div v-show="openGroup === 'accounts'" class="nav-sub">
            <RouterLink to="/accounts/crypto" class="nav-sub-item" :class="{ 'is-on': route.path.startsWith('/accounts/crypto') }">数字钱包</RouterLink>
            <RouterLink to="/accounts/cards" class="nav-sub-item" :class="{ 'is-on': route.path.startsWith('/accounts/cards') }">信用卡</RouterLink>
          </div>
        </div>
        <RouterLink to="/servers" class="nav-item" :class="{ 'is-on': route.path.startsWith('/servers') || route.path.startsWith('/keys') }" @click="closeGroups">
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
        <RouterLink to="/settings" class="nav-item" :class="{ 'is-on': route.path.startsWith('/settings') }" @click="closeGroups">
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
        <nav v-if="route.path.startsWith('/dashboard')" class="tabs">
          <RouterLink to="/dashboard" class="tab is-on">仪表盘</RouterLink>
        </nav>
        <nav v-else-if="route.path.startsWith('/settings')" class="tabs">
          <RouterLink to="/settings" custom v-slot="{ href, navigate }">
            <a :href="href" class="tab" :class="{ 'is-on': route.path === '/settings' }" @click="navigate">登录安全</a>
          </RouterLink>
          <RouterLink to="/settings/mcp" class="tab" :class="{ 'is-on': route.path.startsWith('/settings/mcp') }">MCP</RouterLink>
        </nav>
        <nav v-else-if="route.path.startsWith('/accounts/crypto')" class="tabs">
          <RouterLink to="/accounts/crypto" class="tab is-on">钱包实例</RouterLink>
        </nav>
        <nav v-else-if="route.path.startsWith('/accounts/cards')" class="tabs">
          <RouterLink to="/accounts/cards" class="tab is-on">虚拟信用卡</RouterLink>
        </nav>
        <nav v-else-if="route.path.startsWith('/quant/crypto')" class="tabs">
          <RouterLink to="/quant/crypto" custom v-slot="{ href, navigate }">
            <a :href="href" class="tab" :class="{ 'is-on': route.path === '/quant/crypto' }" @click="navigate">概览</a>
          </RouterLink>
          <RouterLink to="/quant/crypto/strategies" class="tab" :class="{ 'is-on': route.path.startsWith('/quant/crypto/strategies') }">交易策略</RouterLink>
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
