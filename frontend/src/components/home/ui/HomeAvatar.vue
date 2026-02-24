<script setup lang="ts">
import { computed } from 'vue'
import maleAvatar from '../../../assets/avatars/default-male.svg'
import femaleAvatar from '../../../assets/avatars/default-female.svg'

const props = withDefaults(defineProps<{
  avatarUrl?: string | null
  gender?: 'male' | 'female' | null
  size?: 'sm' | 'md' | 'lg' | 'xl'
  alt?: string
}>(), {
  avatarUrl: null,
  gender: null,
  size: 'sm',
  alt: 'avatar',
})

const sizeClass = computed(() => {
  if (props.size === 'md') return 'hv-avatar--md'
  if (props.size === 'lg') return 'hv-avatar--lg'
  if (props.size === 'xl') return 'hv-avatar--xl'
  return ''
})

// 有上传头像时用上传图；否则按性别选默认插画
const imgSrc = computed(() => {
  if (props.avatarUrl) return props.avatarUrl
  return props.gender === 'female' ? femaleAvatar : maleAvatar
})
</script>

<template>
  <div class="hv-avatar hv-avatar--img" :class="sizeClass">
    <img :src="imgSrc" :alt="alt" />
  </div>
</template>

<style scoped>
.hv-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  overflow: hidden;
}

.hv-avatar--md {
  width: 38px;
  height: 38px;
}

.hv-avatar--lg {
  width: 44px;
  height: 44px;
}

.hv-avatar--xl {
  width: 72px;
  height: 72px;
}

.hv-avatar--img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
