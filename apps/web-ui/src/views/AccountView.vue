<script setup lang="ts">
import QRCode from "qrcode";
import { onMounted, ref } from "vue";
import { ApiError, api } from "../api";
import { useAuth } from "../stores/auth";

const auth = useAuth();
const error = ref("");
const message = ref("");
const setup = ref<{ secret: string; otpauth_uri: string } | null>(null);
const qrDataUrl = ref("");
const confirmCode = ref("");
const disablePassword = ref("");
const disableCode = ref("");
const currentPassword = ref("");
const newPassword = ref("");
const busy = ref(false);

onMounted(() => auth.refresh());

async function beginSetup() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const created = await api<{ secret: string; otpauth_uri: string }>("/api/auth/totp/setup", { method: "POST" });
    qrDataUrl.value = await QRCode.toDataURL(created.otpauth_uri, { margin: 1, width: 196 });
    setup.value = created;
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "无法开始设置";
  } finally {
    busy.value = false;
  }
}

async function confirmSetup() {
  error.value = "";
  busy.value = true;
  try {
    await api("/api/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code: confirmCode.value }) });
    setup.value = null;
    qrDataUrl.value = "";
    confirmCode.value = "";
    message.value = "两步验证已开启";
    await auth.refresh();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "确认失败";
  } finally {
    busy.value = false;
  }
}

async function disable() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    await api("/api/auth/totp/disable", {
      method: "POST",
      body: JSON.stringify({ password: disablePassword.value, code: disableCode.value }),
    });
    disablePassword.value = "";
    disableCode.value = "";
    message.value = "两步验证已关闭";
    await auth.refresh();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "关闭失败";
  } finally {
    busy.value = false;
  }
}

async function changePassword() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    await api("/api/auth/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword.value, new_password: newPassword.value }),
    });
    currentPassword.value = "";
    newPassword.value = "";
    message.value = "密码已修改";
    await auth.refresh();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "修改失败";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <p v-if="message" class="banner ok">{{ message }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>登录安全</h1>
    </header>
    <div class="panel-body">
      <p class="muted" style="margin-top: 0">账户 {{ auth.username || "—" }}。两步验证可以随时开启或关闭。</p>
      <p>两步验证：<strong>{{ auth.totpEnabled ? "已开启" : "未开启" }}</strong></p>

      <template v-if="!auth.totpEnabled">
        <button v-if="!setup" class="primary" type="button" :disabled="busy" @click="beginSetup">开启两步验证</button>
        <form v-else class="panel-form" @submit.prevent="confirmSetup">
          <p class="muted">用验证器扫描二维码，或手动添加下面的密钥，再填写它给出的 6 位验证码。确认后才会真正开启。</p>
          <img class="qr" :src="qrDataUrl" width="196" height="196" alt="两步验证二维码" />
          <p class="mono">{{ setup.secret }}</p>
          <label>验证码<input v-model="confirmCode" inputmode="numeric" maxlength="6" required /></label>
          <div class="row">
            <button class="primary" type="submit" :disabled="busy">确认开启</button>
            <button class="link" type="button" @click="setup = null; qrDataUrl = ''">取消</button>
          </div>
        </form>
      </template>
      <form v-else class="panel-form" @submit.prevent="disable">
        <label>密码<input v-model="disablePassword" type="password" autocomplete="current-password" required /></label>
        <label>验证码<input v-model="disableCode" inputmode="numeric" maxlength="6" required /></label>
        <button class="primary" type="submit" :disabled="busy">关闭两步验证</button>
      </form>
    </div>
  </section>

  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>修改密码</h1>
    </header>
    <div class="panel-body">
      <form class="panel-form" @submit.prevent="changePassword">
        <label>当前密码<input v-model="currentPassword" type="password" autocomplete="current-password" required /></label>
        <label>新密码<input v-model="newPassword" type="password" autocomplete="new-password" required /></label>
        <button class="primary" type="submit" :disabled="busy">保存</button>
      </form>
    </div>
  </section>
</template>
