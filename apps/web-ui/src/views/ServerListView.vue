<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, api, formatTime, reachabilityLabel, type ServerSummary } from "../api";
import StatusPill from "../components/StatusPill.vue";

const router = useRouter();
const servers = ref<ServerSummary[]>([]);
const error = ref("");
const query = ref("");

onMounted(async () => {
  try {
    servers.value = await api<ServerSummary[]>("/api/servers");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
});

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
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>服务器 <em class="count">{{ visible.length }}</em></h1>
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
            <td>{{ server.docker_version || "—" }}</td>
            <td>{{ countText(server) }}</td>
            <td>{{ formatTime(server.last_checked_at) }}</td>
            <td><RouterLink class="op" :to="`/servers/${server.id}`" @click.stop>查看</RouterLink></td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="panel-foot">共 {{ visible.length }} 条</footer>
  </section>
</template>
