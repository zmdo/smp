<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { ApiError, api } from "../api";

const props = defineProps<{ id: string; name: string }>();
const emit = defineEmits<{ saved: [name: string]; failed: [message: string] }>();

const editing = ref(false);
const draft = ref(props.name);
const input = ref<HTMLInputElement | null>(null);
const saving = ref(false);

watch(
  () => props.name,
  (name) => {
    if (!editing.value) draft.value = name;
  },
);

async function start() {
  draft.value = props.name;
  editing.value = true;
  await nextTick();
  input.value?.focus();
  input.value?.select();
}

function cancel() {
  editing.value = false;
  draft.value = props.name;
}

async function save() {
  if (!editing.value || saving.value) return;
  const name = draft.value.trim();
  if (!name || name === props.name) {
    cancel();
    return;
  }
  saving.value = true;
  try {
    await api(`/api/servers/${props.id}`, { method: "PATCH", body: JSON.stringify({ name }) });
    emit("saved", name);
    editing.value = false;
  } catch (err) {
    emit("failed", err instanceof ApiError ? err.message : "名称保存失败");
    input.value?.focus();
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <span class="copy-line" @click.stop>
    <input
      v-if="editing"
      ref="input"
      v-model="draft"
      class="name-edit"
      maxlength="80"
      @keydown.enter.prevent="save"
      @keydown.esc.prevent="cancel"
      @blur="save"
    />
    <template v-else>
      <span class="name-text">{{ name }}</span>
      <button class="pen" type="button" title="修改名称" @click="start">
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M2.8 11.5 2.2 13.8 4.5 13.2 12.7 5 11 3.3 2.8 11.5Z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" />
          <path d="M10.1 4.2 11.8 5.9" fill="none" stroke="currentColor" stroke-width="1.3" />
        </svg>
      </button>
    </template>
  </span>
</template>
