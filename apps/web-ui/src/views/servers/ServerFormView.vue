<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError, api, type ComponentInfo, type ServerDetail, type ServerGroup, type SshKey } from "../../api";

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
const groups = ref<ServerGroup[]>([]);
const groupId = ref("");
const region = ref("");
const error = ref("");
const notice = ref("");
const submitting = ref(false);
const testing = ref(false);
const testedSignature = ref("");

const connectionSignature = computed(() =>
  JSON.stringify({
    host: intranetHost.value.trim(),
    port: Number(sshPort.value),
    user: sshUser.value.trim(),
    auth: authMethod.value,
    keySource: keySource.value,
    keyId: selectedKeyId.value,
    secret: secret.value,
  }),
);
const canSave = computed(
  () => isEdit.value || (testedSignature.value !== "" && testedSignature.value === connectionSignature.value),
);

watch(connectionSignature, () => {
  testedSignature.value = "";
  notice.value = "";
});

onMounted(async () => {
  try {
    keys.value = await api<SshKey[]>("/api/ssh-keys");
    components.value = await api<ComponentInfo[]>("/api/components");
    groups.value = await api<ServerGroup[]>("/api/server-groups");
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
    groupId.value = server.group_id || "";
    region.value = server.region || "";
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

function authProblem(): string {
  if (!intranetHost.value.trim() || !sshUser.value.trim()) return "请填写地址和 SSH 用户";
  if (authMethod.value === "password") {
    if (!secret.value.trim()) return "请填写口令";
    return "";
  }
  if (keySource.value === "existing") {
    if (!selectedKeyId.value) return "请选择一把密钥";
    return "";
  }
  if (!secret.value.trim()) return "请粘贴私钥";
  return "";
}

function connectionBody(): Record<string, unknown> {
  const body: Record<string, unknown> = {
    intranet_host: intranetHost.value,
    ssh_port: Number(sshPort.value),
    ssh_user: sshUser.value,
    auth_method: authMethod.value,
  };
  if (authMethod.value === "password" || keySource.value === "new") body.secret = secret.value;
  else body.ssh_key_id = selectedKeyId.value;
  return body;
}

async function testConnection() {
  error.value = "";
  notice.value = "";
  const problem = authProblem();
  if (problem) {
    error.value = problem;
    testedSignature.value = "";
    return;
  }
  const signature = connectionSignature.value;
  testing.value = true;
  testedSignature.value = "";
  try {
    const result = await api<{ ok: boolean; message: string }>("/api/servers/test-connection", {
      method: "POST",
      body: JSON.stringify(connectionBody()),
    });
    if (connectionSignature.value !== signature) return;
    if (result.ok) {
      testedSignature.value = signature;
      notice.value = result.message;
    } else {
      error.value = result.message;
    }
  } catch (err) {
    if (connectionSignature.value === signature) {
      error.value = err instanceof ApiError ? err.message : "连接测试失败";
    }
  } finally {
    testing.value = false;
  }
}

async function submit() {
  error.value = "";
  if (!isEdit.value && !canSave.value) {
    error.value = "请先测试连接";
    return;
  }
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
    ssh_port: Number(sshPort.value),
    ssh_user: sshUser.value,
    auth_method: authMethod.value,
  };
  if (!isEdit.value) body.intranet_host = intranetHost.value;
  if (authMethod.value === "password") {
    if (secret.value) body.secret = secret.value;
  } else if (keySource.value === "existing") {
    body.ssh_key_id = selectedKeyId.value;
  } else if (secret.value.trim()) {
    body.secret = secret.value;
    body.ssh_key_name = keyName.value;
  }
  body.group_id = groupId.value || null;
  body.region = region.value.trim();
  if (!isEdit.value) {
    body.auto_install = autoInstall.value;
    body.component_ids = autoInstall.value ? selectedComponents.value : [];
    if (autoInstall.value && selectedComponents.value.length === 0) {
      error.value = "请选择要安装的组件";
      submitting.value = false;
      return;
    }
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
      <p class="muted" style="margin-top: 0">{{ isEdit ? "地址登记后不能修改。区域、登录方式和分组仍可以调整。" : "填写这台机器的 IP，公网或内网都可以。区域留空时，内网记为内网，外网按 IP 自动查询。需要 Docker 时可以在下面勾选自动安装，也可以连上之后再装。" }}</p>
      <form class="panel-form" @submit.prevent="submit">
        <p v-if="error" class="banner error">{{ error }}</p>
        <p v-if="notice" class="banner ok">{{ notice }}</p>
        <label>名称<input v-model="name" required maxlength="80" /></label>
        <label>
          分组
          <select v-model="groupId">
            <option value="">未分组</option>
            <option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option>
          </select>
        </label>
        <label>地址<input v-model="intranetHost" :disabled="isEdit" required placeholder="例如 10.0.0.8" /></label>
        <label>区域<input v-model="region" maxlength="80" placeholder="留空则自动判断，内网为内网" /></label>
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
        <template v-if="!isEdit">
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
        </template>
        <div class="row">
          <button v-if="!isEdit" class="secondary" type="button" :disabled="testing || submitting" @click="testConnection">
            {{ testing ? "测试中" : "测试连接" }}
          </button>
          <button class="primary" type="submit" :disabled="submitting || testing || !canSave">保存</button>
          <RouterLink class="link" :to="isEdit ? `/servers/${serverId}` : '/servers'">取消</RouterLink>
        </div>
        <p v-if="!isEdit" class="muted">先测试连接，通过后才能保存。</p>
      </form>
    </div>
  </section>
</template>
