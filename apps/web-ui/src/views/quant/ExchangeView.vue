<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ApiError, api, formatTime } from "../../api";

interface VenueField {
  key: string;
  label: string;
}

interface Venue {
  id: string;
  name: string;
  wallet: string;
  fields: VenueField[];
}

interface Balance {
  asset: string;
  free: string;
  locked: string;
  total: string;
}

interface ExchangeAccount {
  id: string;
  name: string;
  venue: string;
  venue_name: string;
  wallet: string;
  balances: Balance[];
  balance_error: string;
  checked_at: string | null;
  created_at: string;
}

const venues = ref<Venue[]>([]);
const rows = ref<ExchangeAccount[]>([]);
const error = ref("");
const creating = ref(false);
const submitting = ref(false);
const refreshing = ref("");
const name = ref("");
const venueId = ref("");
const credentials = ref<Record<string, string>>({});
const selectedId = ref("");

const venue = computed(() => venues.value.find((item) => item.id === venueId.value) || venues.value[0]);
const selected = computed(() => rows.value.find((item) => item.id === selectedId.value) || null);

onMounted(async () => {
  try {
    venues.value = await api<Venue[]>("/api/exchanges/venues");
    venueId.value = venues.value[0]?.id || "";
    resetCredentials();
    await load();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
});

async function load() {
  rows.value = await api<ExchangeAccount[]>("/api/exchanges");
  if (selectedId.value && !rows.value.some((item) => item.id === selectedId.value)) selectedId.value = "";
  if (!selectedId.value && rows.value[0]) selectedId.value = rows.value[0].id;
}

function resetCredentials() {
  const next: Record<string, string> = {};
  for (const field of venue.value?.fields || []) next[field.key] = "";
  credentials.value = next;
}

function chooseVenue() {
  resetCredentials();
}

function openForm() {
  error.value = "";
  name.value = "";
  venueId.value = venues.value[0]?.id || "";
  resetCredentials();
  creating.value = true;
}

function summary(account: ExchangeAccount): string {
  if (account.balance_error && account.balances.length === 0) return "查询失败";
  if (!account.checked_at) return "尚未查询";
  if (account.balances.length === 0) return "没有余额";
  return account.balances
    .slice(0, 3)
    .map((item) => `${item.asset} ${item.total}`)
    .join("，");
}

async function submit() {
  error.value = "";
  submitting.value = true;
  try {
    const created = await api<ExchangeAccount>("/api/exchanges", {
      method: "POST",
      body: JSON.stringify({ name: name.value, venue: venueId.value, credentials: credentials.value }),
    });
    creating.value = false;
    await load();
    selectedId.value = created.id;
    if (created.balance_error) error.value = created.balance_error;
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "保存失败";
  } finally {
    submitting.value = false;
  }
}

async function refresh(account: ExchangeAccount) {
  error.value = "";
  refreshing.value = account.id;
  try {
    const updated = await api<ExchangeAccount>(`/api/exchanges/${account.id}/refresh`, { method: "POST" });
    selectedId.value = updated.id;
    await load();
    if (updated.balance_error) error.value = updated.balance_error;
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "查询余额失败";
  } finally {
    refreshing.value = "";
  }
}

async function remove(account: ExchangeAccount) {
  if (!window.confirm(`删除交易所「${account.name}」？不会影响交易所里的资产。`)) return;
  error.value = "";
  try {
    await api(`/api/exchanges/${account.id}`, { method: "DELETE" });
    if (selectedId.value === account.id) selectedId.value = "";
    await load();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "删除失败";
  }
}
</script>

<template>
  <p v-if="error" class="banner error">{{ error }}</p>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>交易所</h1>
      <div class="tools">
        <button class="icon" type="button" title="加入交易所" @click="openForm">+</button>
      </div>
    </header>
    <div class="panel-body">
      <form v-if="creating" class="panel-form" @submit.prevent="submit">
        <p class="muted" style="margin-top: 0">只读取余额，不会下单或提币。API 需要有读取权限，并把这台电脑的出口 IP 加到交易所白名单。</p>
        <label>名称<input v-model="name" required maxlength="80" placeholder="例如 币安主账户" /></label>
        <label>
          交易所
          <select v-model="venueId" @change="chooseVenue">
            <option v-for="item in venues" :key="item.id" :value="item.id">{{ item.name }}（{{ item.wallet }}）</option>
          </select>
        </label>
        <label v-for="field in venue?.fields || []" :key="field.key">
          {{ field.label }}
          <input v-model="credentials[field.key]" type="password" required autocomplete="off" />
        </label>
        <div class="row">
          <button class="primary" type="submit" :disabled="submitting">{{ submitting ? "查询中" : "保存并查询余额" }}</button>
          <button class="link" type="button" @click="creating = false">取消</button>
        </div>
      </form>
      <p v-if="!creating && rows.length === 0" class="empty">还没有交易所。点右上角加入。</p>
      <div v-if="rows.length" class="table-wrap">
        <table class="clickable">
          <thead>
            <tr>
              <th>名称</th>
              <th>交易所</th>
              <th>余额</th>
              <th>最近查询</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="account in rows" :key="account.id" @click="selectedId = account.id">
              <td>{{ account.name }}</td>
              <td>{{ account.venue_name }}</td>
              <td>{{ summary(account) }}</td>
              <td>{{ formatTime(account.checked_at) }}</td>
              <td class="ops" @click.stop>
                <button class="link" type="button" :disabled="refreshing === account.id" @click="refresh(account)">
                  {{ refreshing === account.id ? "查询中" : "刷新余额" }}
                </button>
                <button class="link danger" type="button" @click="remove(account)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
  <section v-if="selected" class="panel">
    <header class="panel-head">
      <h2><i class="mark"></i>{{ selected.name }} · {{ selected.venue_name }} {{ selected.wallet }}</h2>
    </header>
    <p v-if="selected.balance_error" class="banner error">{{ selected.balance_error }}</p>
    <p v-if="selected.balances.length === 0" class="empty">{{ selected.checked_at ? "没有非零余额。" : "还没有查询过余额。" }}</p>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>币种</th>
            <th>可用</th>
            <th>冻结</th>
            <th>合计</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in selected.balances" :key="item.asset">
            <td>{{ item.asset }}</td>
            <td class="mono">{{ item.free }}</td>
            <td class="mono">{{ item.locked }}</td>
            <td class="mono">{{ item.total }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
