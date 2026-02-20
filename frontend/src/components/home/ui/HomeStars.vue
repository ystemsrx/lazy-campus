<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  max?: number
  size?: 'sm' | 'md'
}>(), {
  max: 5,
  size: 'md',
})

const stars = computed(() => Array.from({ length: props.max }, (_, i) => i < props.value))
</script>

<template>
  <span class="hv-stars" :class="{ 'hv-stars--sm': size === 'sm' }">
    <i
      v-for="(filled, idx) in stars"
      :key="idx"
      :class="filled ? 'fa-solid fa-star' : 'fa-regular fa-star'"
    ></i>
  </span>
</template>

<style scoped>
.hv-stars {
  color: #f59e0b;
  font-size: var(--text-sm);
  letter-spacing: 1px;
}

.hv-stars--sm {
  font-size: var(--text-xs);
}
</style>
