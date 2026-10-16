<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{ value: string }>();
const copied = ref(false);
let timer = 0;

async function copy() {
  const text = props.value;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "true");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  copied.value = true;
  window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    copied.value = false;
  }, 1200);
}
</script>

<template>
  <button class="copy" type="button" :title="copied ? '已复制' : '复制'" @click.stop="copy">
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <rect x="5.2" y="5.2" width="8.3" height="8.3" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.4" />
      <path d="M10.2 5.2V3.4A1.2 1.2 0 0 0 9 2.2H3.4A1.2 1.2 0 0 0 2.2 3.4V9A1.2 1.2 0 0 0 3.4 10.2H5.2" fill="none" stroke="currentColor" stroke-width="1.4" />
    </svg>
  </button>
</template>
