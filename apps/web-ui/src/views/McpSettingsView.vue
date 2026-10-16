<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ApiError, api } from "../api";

interface McpSettings {
  enabled: boolean;
  has_token: boolean;
  token_last4: string | null;
  expose_servers: boolean;
  expose_wallets: boolean;
  expose_cards: boolean;
}

const error = ref("");
const message = ref("");
const busy = ref(false);
const enabled = ref(false);
const hasToken = ref(false);
const tokenLast4 = ref<string | null>(null);
const exposeServers = ref(true);
const exposeWallets = ref(true);
const exposeCards = ref(true);
const freshToken = ref("");

const endpoint = computed(() => `${window.location.origin}/mcp`);
const snippet = computed(() => {
  const token = freshToken.value || "在这里粘贴令牌";
  return JSON.stringify(
    {
      mcpServers: {
        策略控制台: {
          url: endpoint.value,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );
});

onMounted(load);

async function load() {
  try {
    const settings = await api<McpSettings>("/api/mcp");
    apply(settings);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

function apply(settings: McpSettings) {
  enabled.value = settings.enabled;
  hasToken.value = settings.has_token;
  tokenLast4.value = settings.token_last4;
  exposeServers.value = settings.expose_servers;
  exposeWallets.value = settings.expose_wallets;
  exposeCards.value = settings.expose_cards;
}

async function save() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const settings = await api<McpSettings>("/api/mcp", {
      method: "POST",
      body: JSON.stringify({
        enabled: enabled.value,
        expose_servers: exposeServers.value,
        expose_wallets: exposeWallets.value,
        expose_cards: exposeCards.value,
      }),
    });
    apply(settings);
    message.value = "已保存";
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "保存失败";
  } finally {
    busy.value = false;
  }
}

async function rotate() {
  if (hasToken.value && !window.confirm("重置后，原来的令牌会立即失效。")) return;
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const created = await api<{ token: string; token_last4: string }>("/api/mcp/token", { method: "POST" });
    freshToken.value = created.token;
    hasToken.value = true;
    tokenLast4.value = created.token_last4;
    message.value = "新令牌只显示这一次，请马上复制。";
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "无法生成令牌";
  } finally {
    busy.value = false;
  }
}

async function copy(text: string) {
  error.value = "";
  try {
    await navigator.clipboard.writeText(text);
    message.value = "已复制";
  } catch {
    error.value = "复制失败";
  }
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <p v-if="message" class="banner ok">{{ message }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>MCP</h1>
    </header>
    <div class="panel-body">
      <p class="muted">
        控制台提供一个只读 MCP 接口。客户端用下面的地址和令牌连接后，只能读取勾选的内容，不会拿到卡号、安全码、助记词或 SSH 私钥。
      </p>
      <form class="panel-form" @submit.prevent="save">
        <label class="check"><input v-model="enabled" type="checkbox" />开启 MCP</label>
        <label class="check"><input v-model="exposeServers" type="checkbox" />服务器和容器</label>
        <label class="check"><input v-model="exposeWallets" type="checkbox" />钱包地址</label>
        <label class="check"><input v-model="exposeCards" type="checkbox" />虚拟信用卡摘要（只有尾号）</label>
        <button class="primary" type="submit" :disabled="busy">保存</button>
      </form>
    </div>
  </section>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>连接信息</h1>
    </header>
    <div class="panel-body">
      <p>端点</p>
      <p class="mono">{{ endpoint }}</p>
      <p>
        令牌
        <template v-if="hasToken">已设置，尾号 {{ tokenLast4 }}</template>
        <template v-else>尚未生成</template>
      </p>
      <p v-if="freshToken" class="mono">{{ freshToken }}</p>
      <div class="row">
        <button class="primary" type="button" :disabled="busy" @click="rotate">{{ hasToken ? "重置令牌" : "生成令牌" }}</button>
        <button v-if="freshToken" class="link" type="button" @click="copy(freshToken)">复制令牌</button>
        <button class="link" type="button" @click="copy(endpoint)">复制端点</button>
      </div>
      <p class="sub">把下面这段放进客户端的 MCP 配置。令牌重置后，旧配置会失效。</p>
      <pre class="config">{{ snippet }}</pre>
    </div>
  </section>
</template>
