<script setup lang="ts">
defineProps<{ value: string; label: string }>();
</script>

<template>
  <span class="pill" :class="value">{{ label }}</span>
</template>
