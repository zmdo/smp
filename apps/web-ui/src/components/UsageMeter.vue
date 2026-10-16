<script setup lang="ts">
import { usageLevel } from "../usage";

defineProps<{
  caption: string;
  percent: number | null;
}>();
</script>

<template>
  <div v-if="percent !== null" class="meter">
    <div class="meter-label"><span>{{ caption }}</span><span>{{ percent }}%</span></div>
    <div class="meter-track"><i class="meter-bar" :class="usageLevel(percent)" :style="{ width: percent + '%' }"></i></div>
  </div>
  <span v-else>—</span>
</template>
