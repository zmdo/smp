<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ApiError, api, formatTime, type SshKey } from "../api";

const keys = ref<SshKey[]>([]);
const error = ref("");
const query = ref("");
const creating = ref(false);
const name = ref("");
const secret = ref("");
const submitting = ref(false);

const visible = computed(() => {
  const text = query.value.trim().toLowerCase();
  if (!text) return keys.value;
  return keys.value.filter((item) => `${item.name} ${item.fingerprint}`.toLowerCase().includes(text));
});

onMounted(load);

async function load() {
  try {
    keys.value = await api<SshKey[]>("/api/ssh-keys");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

async function create() {
  error.value = "";
  submitting.value = true;
  try {
    await api("/api/ssh-keys", {
      method: "POST",
      body: JSON.stringify({ name: name.value, secret: secret.value }),
    });
    name.value = "";
    secret.value = "";
    creating.value = false;
    await load();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "保存失败";
  } finally {
    submitting.value = false;
  }
}

async function remove(item: SshKey) {
  if (!window.confirm(`删除密钥「${item.name}」？`)) return;
  error.value = "";
  try {
    await api(`/api/ssh-keys/${item.id}`, { method: "DELETE" });
    await load();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "删除失败";
  }
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section v-if="creating" class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>添加密钥</h1>
    </header>
    <div class="panel-body">
      <form class="panel-form" @submit.prevent="create">
        <label>名称<input v-model="name" required maxlength="80" placeholder="例如 机房跳板" /></label>
        <label>
          私钥
          <textarea v-model="secret" class="mono" required spellcheck="false" placeholder="粘贴 PEM 私钥" />
        </label>
        <div class="row">
          <button class="primary" type="submit" :disabled="submitting">保存</button>
          <button class="link" type="button" @click="creating = false">取消</button>
        </div>
      </form>
    </div>
  </section>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>服务器密钥 <em class="count">{{ visible.length }}</em></h1>
      <div class="tools">
        <input v-model="query" class="search" type="search" placeholder="搜索" />
        <button class="icon" type="button" title="添加密钥" @click="creating = true">+</button>
      </div>
    </header>
    <div v-if="visible.length === 0" class="empty">{{ keys.length === 0 ? "还没有密钥。点右上角添加，或在登记服务器实例时粘贴一把新私钥。" : "没有匹配的密钥。" }}</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>指纹</th>
            <th>使用中</th>
            <th>添加时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in visible" :key="item.id">
            <td>{{ item.name }}</td>
            <td class="mono">{{ item.fingerprint }}</td>
            <td>{{ item.server_count }} 台服务器</td>
            <td>{{ formatTime(item.created_at) }}</td>
            <td><button class="link danger" type="button" @click="remove(item)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="panel-foot">共 {{ visible.length }} 条</footer>
  </section>
</template>
