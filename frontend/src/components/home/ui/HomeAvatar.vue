<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  avatarUrl?: string | null
  gender?: 'male' | 'female' | null
  size?: 'sm' | 'lg' | 'xl'
  alt?: string
}>(), {
  avatarUrl: null,
  gender: null,
  size: 'sm',
  alt: 'avatar',
})

const sizeClass = computed(() => {
  if (props.size === 'lg') return 'hv-avatar--lg'
  if (props.size === 'xl') return 'hv-avatar--xl'
  return ''
})

const genderClass = computed(() => (props.gender === 'female' ? 'hv-avatar--female' : 'hv-avatar--male'))
</script>

<template>
  <div v-if="avatarUrl" class="hv-avatar hv-avatar--img" :class="sizeClass">
    <img :src="avatarUrl" :alt="alt" />
  </div>
  <div v-else class="hv-avatar" :class="[sizeClass, genderClass]">
    <i class="fa-solid fa-user"></i>
  </div>
</template>

<style scoped>
.hv-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--c-accent-soft), var(--c-accent));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
  overflow: hidden;
}

.hv-avatar--lg {
  width: 44px;
  height: 44px;
  font-size: 17px;
}

.hv-avatar--xl {
  width: 72px;
  height: 72px;
  font-size: 28px;
}

.hv-avatar--male {
  background: linear-gradient(135deg, #93c5fd, #3b82f6);
}

.hv-avatar--female {
  background: linear-gradient(135deg, #f9a8d4, #ec4899);
}

.hv-avatar--img {
  background: none;
}

.hv-avatar--img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
