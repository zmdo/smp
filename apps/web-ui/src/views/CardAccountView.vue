<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ApiError, api } from "../api";
import places from "../geo/places.json";

const countries = places.countries;
const usStates = places.usStates;
const unitedStates = "美国";

interface Card {
  id: string;
  name: string;
  platform: string;
  holder: string;
  expiry: string;
  last4: string;
  country: string;
  region: string;
  city: string;
  address1: string;
  address2: string;
  postal_code: string;
  note: string;
  created_at: string;
}

const cards = ref<Card[]>([]);
const error = ref("");
const creating = ref(false);
const submitting = ref(false);
const name = ref("");
const platform = ref("");
const holder = ref("");
const number = ref("");
const expiry = ref("");
const cvv = ref("");
const country = ref(unitedStates);
const region = ref("");
const city = ref("");
const isUnitedStates = computed(() => country.value === unitedStates);
const cities = computed(() => usStates.find((item) => item.name === region.value)?.cities ?? []);
const address1 = ref("");
const address2 = ref("");
const postalCode = ref("");
const note = ref("");
const revealed = ref<Record<string, { number: string; cvv: string }>>({});

onMounted(load);

async function load() {
  try {
    cards.value = await api<Card[]>("/api/cards");
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "加载失败";
  }
}

async function create() {
  error.value = "";
  submitting.value = true;
  try {
    await api("/api/cards", {
      method: "POST",
      body: JSON.stringify({
        name: name.value,
        platform: platform.value,
        holder: holder.value,
        number: number.value,
        expiry: expiry.value,
        cvv: cvv.value,
        country: country.value,
        region: region.value,
        city: city.value,
        address1: address1.value,
        address2: address2.value,
        postal_code: postalCode.value,
        note: note.value,
      }),
    });
    name.value = "";
    platform.value = "";
    holder.value = "";
    number.value = "";
    expiry.value = "";
    cvv.value = "";
    country.value = unitedStates;
    region.value = "";
    city.value = "";
    address1.value = "";
    address2.value = "";
    postalCode.value = "";
    note.value = "";
    creating.value = false;
    await load();
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "保存失败";
  } finally {
    submitting.value = false;
  }
}

async function reveal(item: Card) {
  error.value = "";
  if (revealed.value[item.id]) {
    const next = { ...revealed.value };
    delete next[item.id];
    revealed.value = next;
    return;
  }
  try {
    revealed.value = {
      ...revealed.value,
      [item.id]: await api(`/api/cards/${item.id}/secret`),
    };
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : "无法查看";
  }
}

function onCountryChange() {
  region.value = "";
  city.value = "";
}

function billing(item: Card) {
  const street = [item.address1, item.address2].filter(Boolean).join(" ");
  return [street, item.city, item.region, item.country, item.postal_code].filter(Boolean).join(", ");
}

async function remove(item: Card) {
  if (!window.confirm(`删除虚拟信用卡「${item.name}」？`)) return;
  error.value = "";
  try {
    await api(`/api/cards/${item.id}`, { method: "DELETE" });
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
      <h1><i class="mark"></i>添加虚拟信用卡</h1>
    </header>
    <div class="panel-body">
      <form class="panel-form" @submit.prevent="create">
        <label>平台<input v-model="platform" required maxlength="80" placeholder="这张卡来自哪个平台" /></label>
        <label>名称<input v-model="name" required maxlength="80" placeholder="例如 日常消费" /></label>
        <label>持卡人<input v-model="holder" required maxlength="80" /></label>
        <label>卡号<input v-model="number" required inputmode="numeric" autocomplete="off" placeholder="可带空格" /></label>
        <label>有效期<input v-model="expiry" required maxlength="5" placeholder="MM/YY" /></label>
        <label>安全码<input v-model="cvv" required maxlength="4" inputmode="numeric" autocomplete="off" /></label>
        <div class="triple">
          <label>
            国家
            <select v-model="country" required @change="onCountryChange">
              <option v-for="item in countries" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label>
            地区/州
            <select v-if="isUnitedStates" v-model="region" required @change="city = ''">
              <option value="" disabled>请选择</option>
              <option v-for="item in usStates" :key="item.code" :value="item.name">{{ item.name }}</option>
            </select>
            <input v-else v-model="region" required maxlength="80" />
          </label>
          <label>
            市
            <select v-if="isUnitedStates" v-model="city" required :disabled="!region">
              <option value="" disabled>请选择</option>
              <option v-for="item in cities" :key="item" :value="item">{{ item }}</option>
            </select>
            <input v-else v-model="city" required maxlength="80" />
          </label>
        </div>
        <label>地址1<input v-model="address1" required maxlength="160" /></label>
        <label>地址2<input v-model="address2" maxlength="160" placeholder="可不填" /></label>
        <label>邮编<input v-model="postalCode" required maxlength="20" /></label>
        <label>备注<input v-model="note" maxlength="500" /></label>
        <div class="row">
          <button class="primary" type="submit" :disabled="submitting">保存</button>
          <button class="link" type="button" @click="creating = false">取消</button>
        </div>
      </form>
    </div>
  </section>
  <section class="panel">
    <header class="panel-head">
      <h1><i class="mark"></i>虚拟信用卡 <em class="count">{{ cards.length }}</em></h1>
      <div class="tools">
        <button class="icon" type="button" title="添加虚拟信用卡" @click="creating = true">+</button>
      </div>
    </header>
    <div v-if="cards.length === 0" class="empty">还没有虚拟信用卡。点右上角添加。</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>平台</th>
            <th>名称</th>
            <th>卡号</th>
            <th>持卡人</th>
            <th>账单地址</th>
            <th>有效期</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in cards" :key="item.id">
            <td>{{ item.platform }}</td>
            <td>{{ item.name }}</td>
            <td class="mono">
              <template v-if="revealed[item.id]">{{ revealed[item.id].number }} · {{ revealed[item.id].cvv }}</template>
              <template v-else>•••• {{ item.last4 }}</template>
            </td>
            <td>{{ item.holder }}</td>
            <td>{{ billing(item) }}</td>
            <td>{{ item.expiry }}</td>
            <td>
              <button class="link" type="button" @click="reveal(item)">{{ revealed[item.id] ? "隐藏" : "查看" }}</button>
              <button class="link danger" type="button" @click="remove(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <footer class="panel-foot">共 {{ cards.length }} 条</footer>
  </section>
</template>
