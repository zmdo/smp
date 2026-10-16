<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, api, formatTime, reachabilityLabel, type ServerSummary } from "../api";
import StatusPill from "../components/StatusPill.vue";

const router = useRouter();
const servers = ref<ServerSummary[]>([]);
const error = ref("");
const query = ref("");
let timer = 0;

onMounted(() => {
  void refresh();
  timer = window.setInterval(() => void refresh(), 1000);
});

onUnmounted(() => window.clearInterval(timer));

async function refresh() {
  try {
    servers.value = await api<ServerSummary[]>("/api/servers");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

const visible = computed(() => {
  const text = query.value.trim().toLowerCase();
  if (!text) return servers.value;
  return servers.value.filter((server) =>
    `${server.name} ${server.intranet_host} ${server.ssh_user}`.toLowerCase().includes(text),
  );
});

function openServer(id: string) {
  router.push(`/servers/${id}`);
}

function countText(server: ServerSummary): string {
  return server.container_count === null ? "—" : String(server.container_count);
}

function usageLevel(percent: number): "ok" | "warn" | "hot" {
  if (percent <= 80) return "ok";
  if (percent < 90) return "warn";
  return "hot";
}

function percentOf(used: number | null, total: number | null): number | null {
  if (used === null || total === null || total <= 0) return null;
  return Math.max(0, Math.min(100, Math.round((used / total) * 100)));
}

function formatBytes(value: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  const digits = size >= 10 || index === 0 ? 0 : 1;
  return `${size.toFixed(digits)} ${units[index]}`;
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>服务器实例 <em class="count">{{ visible.length }}</em></h1>
      <div class="tools">
        <input v-model="query" class="search" type="search" placeholder="搜索" />
        <RouterLink class="icon" to="/servers/new" title="登记服务器">+</RouterLink>
      </div>
    </header>
    <div v-if="visible.length === 0" class="empty">{{ servers.length === 0 ? "还没有服务器。点右上角登记一台机器。" : "没有匹配的服务器。" }}</div>
    <div v-else class="table-wrap">
      <table class="clickable">
        <thead>
          <tr>
            <th>名称</th>
            <th>地址</th>
            <th>状态</th>
            <th>CPU</th>
            <th>内存</th>
            <th>硬盘</th>
            <th>Docker</th>
            <th>容器</th>
            <th>最近检查</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="server in visible" :key="server.id" @click="openServer(server.id)">
            <td>{{ server.name }}</td>
            <td class="mono">{{ server.ssh_user }}@{{ server.intranet_host }}:{{ server.ssh_port }}</td>
            <td><StatusPill :value="server.reachability" :label="reachabilityLabel[server.reachability] || server.reachability" /></td>
            <td>
              <div v-if="server.cpu_percent !== null" class="meter">
                <div class="meter-label"><span>{{ server.cpu_cores }} 核</span><span>{{ server.cpu_percent }}%</span></div>
                <div class="meter-track"><i class="meter-bar" :class="usageLevel(server.cpu_percent)" :style="{ width: server.cpu_percent + '%' }"></i></div>
              </div>
              <span v-else>—</span>
            </td>
            <td>
              <div v-if="percentOf(server.mem_used_bytes, server.mem_total_bytes) !== null" class="meter">
                <div class="meter-label">
                  <span>{{ formatBytes(server.mem_used_bytes || 0) }} / {{ formatBytes(server.mem_total_bytes || 0) }}</span>
                  <span>{{ percentOf(server.mem_used_bytes, server.mem_total_bytes) }}%</span>
                </div>
                <div class="meter-track"><i class="meter-bar" :class="usageLevel(percentOf(server.mem_used_bytes, server.mem_total_bytes) || 0)" :style="{ width: (percentOf(server.mem_used_bytes, server.mem_total_bytes) || 0) + '%' }"></i></div>
              </div>
              <span v-else>—</span>
            </td>
            <td>
              <div v-if="percentOf(server.disk_used_bytes, server.disk_total_bytes) !== null" class="meter">
                <div class="meter-label">
                  <span>{{ formatBytes(server.disk_used_bytes || 0) }} / {{ formatBytes(server.disk_total_bytes || 0) }}</span>
                  <span>{{ percentOf(server.disk_used_bytes, server.disk_total_bytes) }}%</span>
                </div>
                <div class="meter-track"><i class="meter-bar" :class="usageLevel(percentOf(server.disk_used_bytes, server.disk_total_bytes) || 0)" :style="{ width: (percentOf(server.disk_used_bytes, server.disk_total_bytes) || 0) + '%' }"></i></div>
              </div>
              <span v-else>—</span>
            </td>
            <td>{{ server.docker_version || "—" }}</td>
            <td>{{ countText(server) }}</td>
            <td>{{ formatTime(server.last_checked_at) }}</td>
            <td class="ops" @click.stop>
              <RouterLink class="op" :to="`/servers/${server.id}`">查看</RouterLink>
              <RouterLink class="op" :to="`/servers/${server.id}/terminal`">终端</RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="panel-foot">共 {{ visible.length }} 条</footer>
  </section>
</template>
