<script setup lang="ts">
import "./AgentConversationRounds.css";
import type { ConversationRound } from "./agentViewTypes";
import RoundAiFinalBubble from "./conversation/RoundAiFinalBubble.vue";
import RoundAiSnap from "./conversation/RoundAiSnap.vue";
import RoundUserBubble from "./conversation/RoundUserBubble.vue";
import TerminalPanel from "./conversation/TerminalPanel.vue";

const props = defineProps<{
  loading: boolean;
  conversationRounds: ConversationRound[];
  showPendingRoundSkeleton: boolean;
  showSetupSkeleton: boolean;
  terminalHostname: string;
  brailleChar: string;
  snapIndices: Map<number, number>;
  isSessionRunning: boolean;
  runningRoundId: number | null;
}>();

const emit = defineEmits<{
  (
    e: "snap-scroll",
    payload: { event: Event; roundId: number; total: number },
  ): void;
  (e: "terminal-scroll", payload: { event: Event; roundId: number }): void;
}>();

function getSnapIndex(roundId: number, total: number): number {
  return (props.snapIndices.get(roundId) ?? total - 1) + 1;
}
</script>

<template>
  <div class="agent-conversation-rounds">
    <div v-if="loading" class="chat-empty">加载中...</div>
    <div
      v-else-if="conversationRounds.length === 0 && !showSetupSkeleton"
      class="chat-empty"
    >
      还没有消息，先发送你的需求吧。
    </div>

    <div
      v-for="(round, roundIndex) in conversationRounds"
      :key="round.id"
      class="chat-round"
    >
      <RoundUserBubble v-if="round.userMessage" :message="round.userMessage" />

      <template
        v-if="
          showPendingRoundSkeleton &&
          roundIndex === conversationRounds.length - 1
        "
      >
        <div class="chat-ai-snap-wrap">
          <div class="chat-ai-snap-outer chat-ai-snap-outer--glow">
            <div class="chat-ai-snap skeleton-snap">
              <div class="skeleton-lines">
                <div class="skeleton-line skeleton-line--long"></div>
                <div class="skeleton-line skeleton-line--short"></div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="showSetupSkeleton" class="terminal">
          <div class="terminal-titlebar">
            <div class="terminal-dots">
              <span class="terminal-dot terminal-dot--red"></span>
              <span class="terminal-dot terminal-dot--yellow"></span>
              <span class="terminal-dot terminal-dot--green"></span>
            </div>
            <span class="terminal-hostname">{{ terminalHostname }}</span>
          </div>
          <div class="terminal-body">
            <div class="terminal-setup">
              <span class="terminal-setup-text">Setting up the environment</span>
              <span class="terminal-setup-spinner">{{ brailleChar }}</span>
            </div>
          </div>
        </div>
      </template>

      <RoundAiSnap
        v-if="round.aiIntermediate.length"
        :messages="round.aiIntermediate"
        :round-id="round.id"
        :current-index="getSnapIndex(round.id, round.aiIntermediate.length)"
        :is-running-round="isSessionRunning && runningRoundId === round.id"
        @snap-scroll="emit('snap-scroll', $event)"
      />

      <TerminalPanel
        v-if="round.entries.length"
        :round-id="round.id"
        :entries="round.entries"
        :terminal-hostname="terminalHostname"
        :is-session-running="isSessionRunning"
        @terminal-scroll="emit('terminal-scroll', $event)"
      />

      <RoundAiFinalBubble v-if="round.aiFinal" :message="round.aiFinal" />
    </div>
  </div>
</template>

<style>
@property --border-angle {
  syntax: "<angle>";
  initial-value: 0deg;
  inherits: false;
}
</style>
