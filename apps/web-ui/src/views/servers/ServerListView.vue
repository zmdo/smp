<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, api, formatTime, reachabilityLabel, type ServerGroup, type ServerSummary } from "../../api";
import StatusPill from "../../components/StatusPill.vue";
import UsageMeter from "../../components/UsageMeter.vue";
import CopyButton from "../../components/CopyButton.vue";
import NameEditor from "../../components/NameEditor.vue";
import { byteCaption, percentOf } from "../../usage";

const router = useRouter();
const servers = ref<ServerSummary[]>([]);
const groups = ref<ServerGroup[]>([]);
const error = ref("");
const query = ref("");
const groupName = ref("");
const creatingGroup = ref(false);
let timer = 0;

onMounted(() => {
  void refresh();
  timer = window.setInterval(() => void refresh(), 1000);
});

onUnmounted(() => window.clearInterval(timer));

async function refresh() {
  try {
    const [serverRows, groupRows] = await Promise.all([
      api<ServerSummary[]>("/api/servers"),
      api<ServerGroup[]>("/api/server-groups"),
    ]);
    servers.value = serverRows;
    groups.value = groupRows;
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

const sections = computed(() => {
  const text = query.value.trim().toLowerCase();
  const matched = text
    ? servers.value.filter((server) =>
        `${server.name} ${server.intranet_host} ${server.ssh_user} ${server.region || ""} ${server.group_name || ""}`
          .toLowerCase()
          .includes(text),
      )
    : servers.value;
  const named = groups.value.map((group) => ({
    id: group.id,
    name: group.name,
    servers: matched.filter((server) => server.group_id === group.id),
  }));
  const known = new Set(groups.value.map((group) => group.id));
  const loose = matched.filter((server) => !server.group_id || !known.has(server.group_id));
  const visibleGroups = text ? named.filter((section) => section.servers.length > 0) : named;
  if (loose.length > 0 || visibleGroups.length === 0) {
    visibleGroups.push({ id: "", name: "未分组", servers: loose });
  }
  return visibleGroups;
});

const shownCount = computed(() => sections.value.reduce((total, section) => total + section.servers.length, 0));

function openServer(id: string) {
  router.push(`/servers/${id}`);
}

function countText(server: ServerSummary): string {
  return server.container_count === null ? "—" : String(server.container_count);
}

async function createGroup() {
  error.value = "";
  const name = groupName.value.trim();
  if (!name) {
    error.value = "请填写分组名称";
    return;
  }
  creatingGroup.value = true;
  try {
    await api<ServerGroup>("/api/server-groups", { method: "POST", body: JSON.stringify({ name }) });
    groupName.value = "";
    await refresh();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "创建分组失败";
  } finally {
    creatingGroup.value = false;
  }
}

async function removeGroup(id: string) {
  error.value = "";
  try {
    await api(`/api/server-groups/${id}`, { method: "DELETE" });
    await refresh();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "删除分组失败";
  }
}

function renameServer(server: ServerSummary, name: string) {
  server.name = name;
  error.value = "";
}

function renameFailed(message: string) {
  error.value = message;
}

async function moveServer(server: ServerSummary, event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  error.value = "";
  try {
    await api(`/api/servers/${server.id}`, {
      method: "PATCH",
      body: JSON.stringify({ group_id: value || null }),
    });
    await refresh();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "调整分组失败";
    await refresh();
  }
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>服务器实例 <em class="count">{{ shownCount }}</em></h1>
      <div class="tools">
        <form class="group-create" @submit.prevent="createGroup">
          <input v-model="groupName" maxlength="80" placeholder="新分组名称" />
          <button class="secondary" type="submit" :disabled="creatingGroup">新建分组</button>
        </form>
        <input v-model="query" class="search" type="search" placeholder="搜索" />
        <RouterLink class="icon" to="/servers/new" title="登记服务器">+</RouterLink>
      </div>
    </header>
    <div v-if="servers.length === 0 && groups.length === 0" class="empty">还没有服务器。点右上角登记一台机器。</div>
    <div v-else-if="shownCount === 0 && query.trim()" class="empty">没有匹配的服务器。</div>
    <div v-else class="table-wrap">
      <table class="clickable">
        <thead>
          <tr>
            <th>名称</th>
            <th>地址</th>
            <th class="nowrap">区域</th>
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
          <template v-for="section in sections" :key="section.id || 'ungrouped'">
            <tr class="group-head">
              <td colspan="11">
                <strong>{{ section.name }}</strong>
                <em class="count">{{ section.servers.length }}</em>
                <button v-if="section.id" class="link" type="button" @click="removeGroup(section.id)">删除分组</button>
              </td>
            </tr>
            <tr v-if="section.servers.length === 0" class="group-empty">
              <td colspan="11">这个分组还没有服务器。</td>
            </tr>
            <tr v-for="server in section.servers" :key="server.id" @click="openServer(server.id)">
              <td><NameEditor :id="server.id" :name="server.name" @saved="renameServer(server, $event)" @failed="renameFailed" /></td>
              <td class="mono nowrap"><span class="copy-line">{{ server.intranet_host }}<CopyButton :value="server.intranet_host" /></span></td>
              <td class="nowrap">{{ server.region || "—" }}</td>
              <td><StatusPill :value="server.reachability" :label="reachabilityLabel[server.reachability] || server.reachability" /></td>
              <td><UsageMeter :caption="server.cpu_cores ? `${server.cpu_cores} 核` : ''" :percent="server.cpu_percent" /></td>
              <td><UsageMeter :caption="byteCaption(server.mem_used_bytes, server.mem_total_bytes)" :percent="percentOf(server.mem_used_bytes, server.mem_total_bytes)" /></td>
              <td><UsageMeter :caption="byteCaption(server.disk_used_bytes, server.disk_total_bytes)" :percent="percentOf(server.disk_used_bytes, server.disk_total_bytes)" /></td>
              <td>{{ server.docker_version || "—" }}</td>
              <td>{{ countText(server) }}</td>
              <td>{{ formatTime(server.last_checked_at) }}</td>
              <td class="ops" @click.stop>
                <select class="group-pick" :value="server.group_id || ''" @change="moveServer(server, $event)">
                  <option value="">未分组</option>
                  <option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option>
                </select>
                <RouterLink class="op" :to="`/servers/${server.id}`">查看</RouterLink>
                <RouterLink class="op" :to="`/servers/${server.id}/terminal`">终端</RouterLink>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <footer class="panel-foot">共 {{ shownCount }} 条</footer>
  </section>
</template>
