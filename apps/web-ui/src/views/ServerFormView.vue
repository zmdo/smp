<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError, api, type ServerDetail } from "../api";

const route = useRoute();
const router = useRouter();
const serverId = computed(() => (typeof route.params.id === "string" ? route.params.id : ""));
const isEdit = computed(() => serverId.value !== "");

const name = ref("");
const intranetHost = ref("");
const sshPort = ref(22);
const sshUser = ref("");
const authMethod = ref<"private_key" | "password">("private_key");
const secret = ref("");
const error = ref("");
const submitting = ref(false);

onMounted(async () => {
  if (!isEdit.value) return;
  try {
    const server = await api<ServerDetail>(`/api/servers/${serverId.value}`);
    name.value = server.name;
    intranetHost.value = server.intranet_host;
    sshPort.value = server.ssh_port;
    sshUser.value = server.ssh_user;
    authMethod.value = server.auth_method;
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
});

async function submit() {
  error.value = "";
  if (!isEdit.value && !secret.value.trim()) {
    error.value = authMethod.value === "private_key" ? "请粘贴私钥" : "请填写口令";
    return;
  }
  submitting.value = true;
  const body: Record<string, unknown> = {
    name: name.value,
    intranet_host: intranetHost.value,
    ssh_port: Number(sshPort.value),
    ssh_user: sshUser.value,
    auth_method: authMethod.value,
  };
  if (secret.value) body.secret = secret.value;
  try {
    const path = isEdit.value ? `/api/servers/${serverId.value}` : "/api/servers";
    const method = isEdit.value ? "PATCH" : "POST";
    const result = await api<{ server: { id: string }; job: { id: string } | null }>(path, {
      method,
      body: JSON.stringify(body),
    });
    const next = result.job ? `/servers/${result.server.id}?job=${result.job.id}` : `/servers/${result.server.id}`;
    await router.push(next);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "保存失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>{{ isEdit ? "编辑服务器" : "登记服务器" }}</h1>
    </header>
    <div class="panel-body">
      <p class="muted" style="margin-top: 0">通过 SSH 连接这台机器，公网或内网地址都可以。目标机器需要已经装好 Docker Engine 和 Compose 插件。</p>
      <form class="panel-form" @submit.prevent="submit">
        <p v-if="error" class="banner error">{{ error }}</p>
        <label>名称<input v-model="name" required maxlength="80" /></label>
        <label>地址<input v-model="intranetHost" required placeholder="10.0.0.8 或 trade.example.com" /></label>
        <label>SSH 端口<input v-model.number="sshPort" type="number" min="1" max="65535" required /></label>
        <label>SSH 用户<input v-model="sshUser" required maxlength="64" /></label>
        <div class="choices">
          <label><input v-model="authMethod" type="radio" value="private_key" />私钥</label>
          <label><input v-model="authMethod" type="radio" value="password" />口令</label>
        </div>
        <label v-if="authMethod === 'private_key'">
          私钥
          <textarea v-model="secret" class="mono" spellcheck="false" :placeholder="isEdit ? '留空则不修改' : '粘贴 PEM 私钥'" />
        </label>
        <label v-else>
          口令
          <input v-model="secret" type="password" :placeholder="isEdit ? '留空则不修改' : ''" />
        </label>
        <div class="row">
          <button class="primary" type="submit" :disabled="submitting">{{ isEdit ? "保存" : "保存并测试连接" }}</button>
          <RouterLink class="link" :to="isEdit ? `/servers/${serverId}` : '/servers'">取消</RouterLink>
        </div>
      </form>
    </div>
  </section>
</template>
