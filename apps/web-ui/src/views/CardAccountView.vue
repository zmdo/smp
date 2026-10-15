<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ApiError, api, formatTime } from "../api";

interface Card {
  id: string;
  name: string;
  holder: string;
  expiry: string;
  last4: string;
  note: string;
  created_at: string;
}

const cards = ref<Card[]>([]);
const error = ref("");
const creating = ref(false);
const submitting = ref(false);
const name = ref("");
const holder = ref("");
const number = ref("");
const expiry = ref("");
const cvv = ref("");
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
        holder: holder.value,
        number: number.value,
        expiry: expiry.value,
        cvv: cvv.value,
        note: note.value,
      }),
    });
    name.value = "";
    holder.value = "";
    number.value = "";
    expiry.value = "";
    cvv.value = "";
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
        <label>名称<input v-model="name" required maxlength="80" placeholder="例如 日常消费" /></label>
        <label>持卡人<input v-model="holder" required maxlength="80" /></label>
        <label>卡号<input v-model="number" required inputmode="numeric" autocomplete="off" placeholder="可带空格" /></label>
        <label>有效期<input v-model="expiry" required maxlength="5" placeholder="MM/YY" /></label>
        <label>安全码<input v-model="cvv" required maxlength="4" inputmode="numeric" autocomplete="off" /></label>
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
            <th>名称</th>
            <th>卡号</th>
            <th>持卡人</th>
            <th>有效期</th>
            <th>备注</th>
            <th>添加时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in cards" :key="item.id">
            <td>{{ item.name }}</td>
            <td class="mono">
              <template v-if="revealed[item.id]">{{ revealed[item.id].number }} · {{ revealed[item.id].cvv }}</template>
              <template v-else>•••• {{ item.last4 }}</template>
            </td>
            <td>{{ item.holder }}</td>
            <td>{{ item.expiry }}</td>
            <td>{{ item.note || "—" }}</td>
            <td>{{ formatTime(item.created_at) }}</td>
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
