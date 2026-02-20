<script setup lang="ts">
defineProps<{
  icon: string
  text: string
}>()
</script>

<template>
  <div class="hv-empty">
    <i :class="icon + ' hv-empty__icon'"></i>
    <p>{{ text }}</p>
  </div>
</template>

<style scoped>
.hv-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--c-text-muted);
}

.hv-empty__icon {
  display: block;
  font-size: 44px;
  margin-bottom: 14px;
  color: var(--c-border);
}
</style>
