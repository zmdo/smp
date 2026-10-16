<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { ApiError, api, formatTime } from "../../api";

interface WalletRow {
  id: string;
  name: string;
  created_at: string;
}

interface Created {
  id: string;
  name: string;
  mnemonic?: string;
}

const router = useRouter();
const wallets = ref<WalletRow[]>([]);
const error = ref("");
const mode = ref<"list" | "create" | "import" | "backup">("list");
const name = ref("");
const password = ref("");
const mnemonic = ref("");
const createdMnemonic = ref("");
const createdId = ref("");
const saved = ref(false);
const submitting = ref(false);

onMounted(load);

async function load() {
  try {
    wallets.value = await api<WalletRow[]>("/api/wallets");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

function resetForm() {
  name.value = "";
  password.value = "";
  mnemonic.value = "";
  error.value = "";
}

function open(next: "create" | "import") {
  resetForm();
  createdMnemonic.value = "";
  createdId.value = "";
  mode.value = next;
}

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    const created = await api<Created>("/api/wallets", {
      method: "POST",
      body: JSON.stringify({
        name: name.value,
        password: password.value,
        mnemonic: mode.value === "import" ? mnemonic.value : null,
      }),
    });
    password.value = "";
    mnemonic.value = "";
    if (created.mnemonic) {
      createdMnemonic.value = created.mnemonic;
      createdId.value = created.id;
      saved.value = false;
      mode.value = "backup";
    } else {
      await router.push(`/accounts/crypto/${created.id}`);
    }
    await load();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "保存失败";
  } finally {
    submitting.value = false;
  }
}

function finishBackup() {
  const id = createdId.value;
  createdMnemonic.value = "";
  createdId.value = "";
  saved.value = false;
  mode.value = "list";
  if (id) void router.push(`/accounts/crypto/${id}`);
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>

  <section v-if="mode === 'backup'" class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>抄写助记词</h1>
    </header>
    <div class="panel-body">
      <p class="sub">这是唯一一次显示这组助记词。离开本页之后，页面不再保留它。</p>
      <ol class="mnemonic">
        <li v-for="(word, index) in createdMnemonic.split(' ')" :key="index"><span>{{ index + 1 }}</span>{{ word }}</li>
      </ol>
      <label class="check"><input v-model="saved" type="checkbox" />我已经把助记词抄写到离线的地方</label>
      <div class="row">
        <button class="primary" type="button" :disabled="!saved" @click="finishBackup">完成</button>
      </div>
    </div>
  </section>

  <section v-else-if="mode === 'create' || mode === 'import'" class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>{{ mode === "create" ? "创建钱包" : "导入钱包" }}</h1>
    </header>
    <div class="panel-body">
      <form class="panel-form" @submit.prevent="submit">
        <label>名称<input v-model="name" required maxlength="80" placeholder="例如 日常资金" /></label>
        <label v-if="mode === 'import'">
          助记词
          <textarea v-model="mnemonic" required rows="3" autocomplete="off" spellcheck="false" placeholder="12 或 24 个英文单词"></textarea>
        </label>
        <label>登录密码<input v-model="password" required type="password" autocomplete="current-password" /></label>
        <p class="sub">用当前登录密码加密助记词。密码不对就不会保存。</p>
        <div class="row">
          <button class="primary" type="submit" :disabled="submitting">{{ mode === "create" ? "创建" : "导入" }}</button>
          <button class="link" type="button" @click="mode = 'list'">取消</button>
        </div>
      </form>
    </div>
  </section>

  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>钱包实例 <em class="count">{{ wallets.length }}</em></h1>
      <div class="tools">
        <button class="primary" type="button" @click="open('create')">创建钱包</button>
        <button class="link" type="button" @click="open('import')">导入钱包</button>
      </div>
    </header>
    <p v-if="wallets.length === 0" class="empty">还没有钱包实例。可以创建新钱包，或用助记词导入。</p>
    <div v-else class="table-wrap">
      <table class="clickable">
        <thead>
          <tr>
            <th>名称</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in wallets" :key="item.id" @click="router.push(`/accounts/crypto/${item.id}`)">
            <td><RouterLink class="op" :to="`/accounts/crypto/${item.id}`" @click.stop>{{ item.name }}</RouterLink></td>
            <td>{{ formatTime(item.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="panel-foot">共 {{ wallets.length }} 条</footer>
  </section>
</template>
