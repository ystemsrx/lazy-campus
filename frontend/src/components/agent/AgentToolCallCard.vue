<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  toolName: string | null
  toolArguments: string | null
  toolCallId: string | null
}>()

const prettyArguments = computed(() => {
  const raw = props.toolArguments?.trim()
  if (!raw) return ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
})
</script>

<template>
  <div class="agent-tool-card">
    <div class="agent-tool-card__head">
      <i class="fa-solid fa-screwdriver-wrench"></i>
      <span>{{ toolName || 'Tool' }}</span>
      <code v-if="toolCallId">{{ toolCallId }}</code>
    </div>
    <pre v-if="prettyArguments" class="agent-tool-card__args">{{ prettyArguments }}</pre>
    <p v-else class="agent-tool-card__empty">无参数</p>
  </div>
</template>

<style scoped>
.agent-tool-card {
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 12px;
  overflow: hidden;
}

.agent-tool-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid #dbeafe;
  font-size: 12px;
  color: #1e40af;
  font-weight: 600;
}

.agent-tool-card__head code {
  margin-left: auto;
  font-size: 11px;
  color: #1d4ed8;
}

.agent-tool-card__args {
  margin: 0;
  padding: 10px;
  max-height: 180px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  color: #1e3a8a;
}

.agent-tool-card__empty {
  margin: 0;
  padding: 10px;
  font-size: 12px;
  color: #64748b;
}
</style>
