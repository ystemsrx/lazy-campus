<script setup lang="ts">
import { computed } from 'vue'

import { renderRichText } from '../../composables/chat/richText'

import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github.css'

const props = defineProps<{
  content: string
}>()

const renderedHtml = computed(() => renderRichText(props.content))
</script>

<template>
  <div class="rich-text" v-html="renderedHtml"></div>
</template>
