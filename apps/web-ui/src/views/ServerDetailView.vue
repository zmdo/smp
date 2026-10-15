<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ApiError,
  api,
  containerStatusLabel,
  formatTime,
  jobActionLabel,
  jobStatusLabel,
  reachabilityLabel,
  sleep,
  type Job,
  type ServerDetail,
} from "../api";
import StatusPill from "../components/StatusPill.vue";

const route = useRoute();
const router = useRouter();
const server = ref<ServerDetail | null>(null);
const error = ref("");
const currentJob = ref<Job | null>(null);
const busy = ref(false);
let stopped = false;

const serverId = computed(() => String(route.params.id || ""));

onMounted(async () => {
  await load();
  const requested = typeof route.query.job === "string" ? route.query.job : "";
  const running = server.value?.recent_jobs.find((job) => job.status === "queued" || job.status === "running");
  const jobId = requested || running?.id;
  if (jobId) await watchJob(jobId);
});

onUnmounted(() => {
  stopped = true;
});

async function load() {
  try {
    server.value = await api<ServerDetail>(`/api/servers/${serverId.value}`);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

async function watchJob(id: string) {
  busy.value = true;
  try {
    while (!stopped) {
      const job = await api<Job>(`/api/ops-jobs/${id}`);
      currentJob.value = job;
      if (job.status === "succeeded" || job.status === "failed") {
        await load();
        const next = server.value?.recent_jobs.find(
          (item) => item.id !== job.id && (item.status === "queued" || item.status === "running"),
        );
        if (next && !stopped) await watchJob(next.id);
        return;
      }
      await sleep(1000);
    }
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "任务查询失败";
  } finally {
    busy.value = false;
  }
}

async function run(action: "test" | "inspect") {
  error.value = "";
  try {
    const job = await api<Job>(`/api/servers/${serverId.value}/${action}`, { method: "POST" });
    await watchJob(job.id);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "操作失败";
  }
}

async function remove() {
  if (!server.value) return;
  if (!window.confirm(`删除服务器「${server.value.name}」？这不会关闭那台机器上已经在跑的容器。`)) return;
  await api(`/api/servers/${serverId.value}`, { method: "DELETE" });
  await router.push("/servers");
}

const showContainers = computed(() => {
  if (!server.value) return false;
  return server.value.container_count !== null && server.value.reachability !== "docker_unavailable";
});
</script>

<template>
  <div v-if="server">
    <p v-if="error" class="banner error">{{ error }}</p>
    <p v-if="currentJob" class="banner" :class="currentJob.status === 'failed' ? 'error' : currentJob.status === 'succeeded' ? 'ok' : ''">
      {{ jobActionLabel[currentJob.action] || currentJob.action }}：{{ jobStatusLabel[currentJob.status] || currentJob.status }}
      <span v-if="currentJob.output_excerpt">。{{ currentJob.output_excerpt }}</span>
    </p>

    <section class="node-card">
      <div class="node-title">
        <strong>{{ server.name }}</strong>
        <StatusPill :value="server.reachability" :label="reachabilityLabel[server.reachability] || server.reachability" />
      </div>
      <p class="sub mono">{{ server.ssh_user }}@{{ server.intranet_host }}:{{ server.ssh_port }}</p>
      <div class="node-grid">
        <div><span>登录</span>{{ server.auth_method === "private_key" ? (server.ssh_key_name || "密钥") : "口令" }}</div>
        <div><span>Docker</span>{{ server.docker_version || "—" }}</div>
        <div><span>Compose</span>{{ server.compose_version || "—" }}</div>
        <div><span>容器</span>{{ server.container_count === null ? "—" : server.container_count }}</div>
        <div><span>最近检查</span>{{ formatTime(server.last_checked_at) }}</div>
        <div><span>主机指纹</span><span class="mono">{{ server.host_key_fingerprint || "测试连接后记录" }}</span></div>
      </div>
      <div class="node-actions">
        <button class="link" type="button" :disabled="busy" @click="run('test')">测试连接</button>
        <button class="link" type="button" :disabled="busy" @click="run('inspect')">立即刷新</button>
        <RouterLink class="link" :to="`/servers/${server.id}/edit`">编辑</RouterLink>
        <button class="link danger" type="button" :disabled="busy" @click="remove">删除</button>
      </div>
    </section>

    <section class="panel">
      <header class="panel-head">
        <h2><i class="mark"></i>容器 <em class="count">{{ server.containers.length }}</em></h2>
      </header>
      <div class="empty" v-if="server.reachability === 'unknown'">尚未测试连接。</div>
      <div class="empty" v-else-if="server.reachability === 'docker_unavailable'">Docker 检查没有通过。看上面的任务结果，装好 Docker 后再测试连接。</div>
      <div class="empty" v-else-if="!showContainers">还没有成功的巡检。在线后会每 30 秒自动刷新，也可以现在立即刷新。</div>
      <div class="empty" v-else-if="server.containers.length === 0">这台服务器上没有容器。</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>名称</th>
              <th>镜像</th>
              <th>状态</th>
              <th>端口</th>
              <th>来源</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in server.containers" :key="item.container_id">
              <td class="mono">{{ item.name }}</td>
              <td class="mono">{{ item.image }}</td>
              <td><StatusPill :value="item.status" :label="containerStatusLabel[item.status] || item.status" /></td>
              <td class="mono">{{ item.ports || "—" }}</td>
              <td>{{ item.managed ? `本平台${item.strategy_slug ? " / " + item.strategy_slug : ""}` : "其他" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer v-if="server.containers.length" class="panel-foot">巡检时间 {{ formatTime(server.containers[0].observed_at) }}</footer>
    </section>

    <section class="panel">
      <header class="panel-head">
        <h2><i class="mark"></i>最近任务 <em class="count">{{ server.recent_jobs.length }}</em></h2>
      </header>
      <div v-if="server.recent_jobs.length === 0" class="empty">还没有任务。</div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>动作</th>
              <th>状态</th>
              <th>时间</th>
              <th>输出</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in server.recent_jobs" :key="job.id">
              <td>{{ jobActionLabel[job.action] || job.action }}</td>
              <td><StatusPill :value="job.status" :label="jobStatusLabel[job.status] || job.status" /></td>
              <td>{{ formatTime(job.finished_at || job.created_at) }}</td>
              <td>{{ job.output_excerpt || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
