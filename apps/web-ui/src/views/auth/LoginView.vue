<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "../../api";
import { useAuth } from "../../stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuth();
const username = ref("admin");
const password = ref("");
const totpCode = ref("");
const totpRequired = ref(false);
const error = ref("");
const submitting = ref(false);

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    const result = await auth.login(username.value, password.value, totpRequired.value ? totpCode.value : undefined);
    if (result.totp_required) {
      totpRequired.value = true;
      error.value = "这个账户开启了两步验证，请填写验证码";
      return;
    }
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
      <p class="muted">使用用户名和密码登录。开启两步验证后，还需要验证码。</p>
      <p v-if="error" class="banner error">{{ error }}</p>
      <label>
        用户名
        <input v-model="username" autocomplete="username" required />
      </label>
      <label>
        密码
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>
      <label v-if="totpRequired">
        验证码
        <input v-model="totpCode" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required />
      </label>
      <button class="primary" type="submit" :disabled="submitting">登录</button>
    </form>
  </div>
</template>
