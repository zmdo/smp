<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "../api";
import { useAuth } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuth();
const password = ref("");
const error = ref("");
const submitting = ref(false);

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    await auth.login(password.value);
    const next = typeof route.query.next === "string" ? route.query.next : "/servers";
    await router.replace(next);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "登录失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <form class="login-card" @submit.prevent="submit">
      <div class="login-brand">
        <span class="logo-mark">策</span>
        <h1>策略控制台</h1>
      </div>
      <p class="muted">登录后管理服务器，并查看上面用 Docker 跑着的服务。</p>
      <p v-if="error" class="banner error">{{ error }}</p>
      <label>
        口令
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>
      <button class="primary" type="submit" :disabled="submitting">登录</button>
    </form>
  </div>
</template>
