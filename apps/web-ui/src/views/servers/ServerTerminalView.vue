<script setup lang="ts">
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api, type ServerSummary } from "../../api";

const route = useRoute();
const host = ref<HTMLElement | null>(null);
const title = ref("终端");
const error = ref("");
let term: Terminal | null = null;
let socket: WebSocket | null = null;
let fit: FitAddon | null = null;
let disposed = false;

onMounted(async () => {
  const id = String(route.params.id);
  try {
    const server = await api<ServerSummary>(`/api/servers/${id}`);
    title.value = `${server.name} · ${server.ssh_user}@${server.intranet_host}`;
  } catch {
    title.value = "终端";
  }
  const element = host.value;
  if (!element) return;
  term = new Terminal({
    cursorBlink: true,
    fontFamily: "Consolas, Cascadia Mono, monospace",
    fontSize: 13,
    theme: { background: "#1e1e1e", foreground: "#e8eaed", cursor: "#e8eaed" },
  });
  fit = new FitAddon();
  term.loadAddon(fit);
  term.open(element);
  fit.fit();
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${location.host}/api/servers/${id}/terminal`);
  socket.binaryType = "arraybuffer";
  socket.onopen = () => sendSize();
  socket.onmessage = (event) => {
    if (!term) return;
    if (typeof event.data === "string") term.write(event.data);
    else term.write(new Uint8Array(event.data));
  };
  socket.onclose = () => {
    if (!disposed) error.value = error.value || "终端连接已断开。";
  };
  socket.onerror = () => {
    error.value = "无法打开终端。";
  };
  term.onData((data) => {
    if (socket?.readyState === WebSocket.OPEN) socket.send(new TextEncoder().encode(data));
  });
  term.onResize(({ cols, rows }) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "resize", cols, rows }));
    }
  });
  window.addEventListener("resize", sendSize);
  term.focus();
});

function sendSize() {
  fit?.fit();
}

onUnmounted(() => {
  disposed = true;
  window.removeEventListener("resize", sendSize);
  socket?.close();
  term?.dispose();
  socket = null;
  term = null;
});
</script>

<template>
  <section class="terminal-page">
    <header class="panel-head">
      <h1><i class="mark"></i>{{ title }}</h1>
      <RouterLink class="link" :to="`/servers/${route.params.id}`">返回</RouterLink>
    </header>
    <p v-if="error" class="banner error">{{ error }}</p>
    <div ref="host" class="terminal-host"></div>
  </section>
</template>
