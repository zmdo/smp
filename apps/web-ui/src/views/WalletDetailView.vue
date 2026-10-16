<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { ApiError, api, formatTime } from "../api";

interface Address {
  chain: string;
  chain_label: string;
  address: string;
  derivation_path: string | null;
  source: "derived" | "manual";
}

interface Account {
  id: string;
  name: string;
  derivation_index: number;
  addresses: Address[];
}

interface Wallet {
  id: string;
  name: string;
  created_at: string;
  accounts: Account[];
}

const route = useRoute();
const wallet = ref<Wallet | null>(null);
const error = ref("");
const copied = ref("");

onMounted(load);

async function load() {
  try {
    wallet.value = await api<Wallet>(`/api/wallets/${route.params.id}`);
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

async function copy(value: string) {
  await navigator.clipboard.writeText(value);
  copied.value = value;
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section v-if="wallet" class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>{{ wallet.name }}</h1>
      <div class="tools">
        <RouterLink class="link" to="/accounts/crypto">返回列表</RouterLink>
      </div>
    </header>
    <div class="panel-body">
      <p class="sub">创建于 {{ formatTime(wallet.created_at) }}</p>
      <div v-for="account in wallet.accounts" :key="account.id" class="account-block">
        <h2>{{ account.name }}</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>链</th>
                <th>收款地址</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in account.addresses" :key="item.chain">
                <td>{{ item.chain_label }}</td>
                <td class="mono">{{ item.address }}</td>
                <td><button class="link" type="button" @click="copy(item.address)">{{ copied === item.address ? "已复制" : "复制" }}</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
