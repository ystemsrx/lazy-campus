<script setup lang="ts">
import type { AgentMessage } from "../../../types/api";

const props = defineProps<{
  messages: AgentMessage[];
  roundId: number;
  currentIndex: number;
  isRunningRound: boolean;
}>();

const emit = defineEmits<{
  (
    e: "snap-scroll",
    payload: { event: Event; roundId: number; total: number },
  ): void;
}>();
</script>

<template>
  <div class="chat-ai-snap-wrap">
    <div
      class="chat-ai-snap-outer"
      :class="{ 'chat-ai-snap-outer--glow': props.isRunningRound }"
    >
      <div
        class="chat-ai-snap"
        @scroll="
          emit('snap-scroll', {
            event: $event,
            roundId: props.roundId,
            total: props.messages.length,
          })
        "
      >
        <div
          v-for="msg in props.messages"
          :key="msg.id"
          class="chat-ai-snap-item"
        >
          <span>{{ msg.content }}</span>
        </div>
      </div>
      <span class="chat-ai-snap-idx"
        >{{ props.currentIndex }}/{{ props.messages.length }}</span
      >
    </div>
  </div>
</template>
