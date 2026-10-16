<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError, api, type ComponentInfo, type ServerDetail, type SshKey } from "../api";

const route = useRoute();
const router = useRouter();
const serverId = computed(() => (typeof route.params.id === "string" ? route.params.id : ""));
const isEdit = computed(() => serverId.value !== "");

const name = ref("");
const intranetHost = ref("");
const sshPort = ref(22);
const sshUser = ref("");
const authMethod = ref<"private_key" | "password">("private_key");
const keySource = ref<"existing" | "new">("new");
const keys = ref<SshKey[]>([]);
const selectedKeyId = ref("");
const keyName = ref("");
const secret = ref("");
const autoInstall = ref(false);
const components = ref<ComponentInfo[]>([]);
const selectedComponents = ref<string[]>([]);
const error = ref("");
const submitting = ref(false);

onMounted(async () => {
  try {
    keys.value = await api<SshKey[]>("/api/ssh-keys");
    components.value = await api<ComponentInfo[]>("/api/components");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "密钥列表加载失败";
  }
  if (!isEdit.value) {
    keySource.value = keys.value.length ? "existing" : "new";
    selectedKeyId.value = keys.value[0]?.id || "";
    return;
  }
  try {
    const server = await api<ServerDetail>(`/api/servers/${serverId.value}`);
    name.value = server.name;
    intranetHost.value = server.intranet_host;
    sshPort.value = server.ssh_port;
    sshUser.value = server.ssh_user;
    authMethod.value = server.auth_method;
    if (server.ssh_key_id) {
      keySource.value = "existing";
      selectedKeyId.value = server.ssh_key_id;
    }
    autoInstall.value = server.auto_install;
    selectedComponents.value = server.component_ids.length
      ? [...server.component_ids]
      : components.value.map((item) => item.id);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
});

function fillComponents() {
  if (autoInstall.value && selectedComponents.value.length === 0) {
    selectedComponents.value = components.value.map((item) => item.id);
  }
}

async function submit() {
  error.value = "";
  if (authMethod.value === "password") {
    if (!isEdit.value && !secret.value.trim()) {
      error.value = "请填写口令";
      return;
    }
  } else if (keySource.value === "existing") {
    if (!selectedKeyId.value) {
      error.value = "请选择一把密钥";
      return;
    }
  } else if (!isEdit.value && !secret.value.trim()) {
    error.value = "请粘贴私钥";
    return;
  } else if (secret.value.trim() && !keyName.value.trim()) {
    error.value = "请填写密钥名称，保存后会出现在服务器密钥里";
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
  if (authMethod.value === "password") {
    if (secret.value) body.secret = secret.value;
  } else if (keySource.value === "existing") {
    body.ssh_key_id = selectedKeyId.value;
  } else if (secret.value.trim()) {
    body.secret = secret.value;
    body.ssh_key_name = keyName.value;
  }
  body.auto_install = autoInstall.value;
  body.component_ids = autoInstall.value ? selectedComponents.value : [];
  if (autoInstall.value && selectedComponents.value.length === 0) {
    error.value = "请选择要安装的组件";
    submitting.value = false;
    return;
  }
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
      <p class="muted" style="margin-top: 0">通过 SSH 连接这台机器，公网或内网地址都可以。需要 Docker 时可以在下面勾选自动安装，也可以连上之后再装。</p>
      <form class="panel-form" @submit.prevent="submit">
        <p v-if="error" class="banner error">{{ error }}</p>
        <label>名称<input v-model="name" required maxlength="80" /></label>
        <label>地址<input v-model="intranetHost" required placeholder="10.0.0.8 或 trade.example.com" /></label>
        <label>SSH 端口<input v-model.number="sshPort" type="number" min="1" max="65535" required /></label>
        <label>SSH 用户<input v-model="sshUser" required maxlength="64" /></label>
        <div class="choices">
          <label><input v-model="authMethod" type="radio" value="private_key" />密钥</label>
          <label><input v-model="authMethod" type="radio" value="password" />口令</label>
        </div>
        <template v-if="authMethod === 'private_key'">
          <div class="choices">
            <label><input v-model="keySource" type="radio" value="existing" :disabled="keys.length === 0" />已有密钥</label>
            <label><input v-model="keySource" type="radio" value="new" />填写密钥</label>
          </div>
          <label v-if="keySource === 'existing'">
            密钥
            <select v-model="selectedKeyId" required>
              <option v-for="item in keys" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>
          <template v-else>
            <label>密钥名称<input v-model="keyName" maxlength="80" placeholder="例如 机房跳板" /></label>
            <label>
              私钥
              <textarea v-model="secret" class="mono" spellcheck="false" :placeholder="isEdit ? '留空则不修改当前密钥' : '粘贴 PEM 私钥'" />
            </label>
            <p class="muted">新粘贴的私钥会自动加入服务器密钥。同一把私钥不会重复保存。</p>
          </template>
        </template>
        <label v-else>
          口令
          <input v-model="secret" type="password" :placeholder="isEdit ? '留空则不修改' : ''" />
        </label>
        <label class="check">
          <input v-model="autoInstall" type="checkbox" @change="fillComponents" />
          自动安装必要组件
        </label>
        <div v-if="autoInstall" class="component-picks">
          <label v-for="item in components" :key="item.id">
            <input v-model="selectedComponents" type="checkbox" :value="item.id" />
            <span>
              <strong>{{ item.name }}</strong>
              <span class="muted">{{ item.summary }}</span>
            </span>
          </label>
          <p v-if="components.length === 0" class="muted">没有可安装的组件。</p>
        </div>
        <div class="row">
          <button class="primary" type="submit" :disabled="submitting">{{ isEdit ? "保存" : "保存并测试连接" }}</button>
          <RouterLink class="link" :to="isEdit ? `/servers/${serverId}` : '/servers'">取消</RouterLink>
        </div>
      </form>
    </div>
  </section>
</template>
