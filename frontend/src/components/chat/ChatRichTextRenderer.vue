<script setup lang="ts">
import { computed } from 'vue'

import { renderRichText } from '../../composables/chat/richText'

import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github.css'

const props = defineProps<{
  content: string
}>()

const renderedHtml = computed(() => renderRichText(props.content))

function onContainerClick(event: MouseEvent) {
  const btn = (event.target as HTMLElement).closest('.code-copy-btn') as HTMLElement | null
  if (!btn) return
  const pre = btn.closest('pre')
  if (!pre) return
  const code = pre.querySelector('code')?.innerText ?? ''
  navigator.clipboard.writeText(code).then(() => {
    btn.classList.add('copied')
    setTimeout(() => btn.classList.remove('copied'), 1500)
  })
}
</script>

<template>
  <div class="rich-text" v-html="renderedHtml" @click="onContainerClick"></div>
</template>
