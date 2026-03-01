<script setup lang="ts">
import type { TerminalEntry } from "../../agentViewTypes";

defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--task">
      <div class="terminal-tool-head terminal-tool-head--task">
        <i class="fa-solid fa-robot"></i>
        <span>Task</span>
        <span v-if="entry.args?.subagent_name" class="terminal-task-badge">{{
          entry.args.subagent_name
        }}</span>
      </div>
      <div v-if="entry.args?.description" class="terminal-tool-detail">
        <span class="terminal-tool-key">desc</span>
        <span class="terminal-tool-val">{{ entry.args.description }}</span>
      </div>
      <div v-if="entry.outputText" class="terminal-task-output">
        <div class="terminal-task-output-label">
          <i class="fa-solid fa-comment-dots"></i>
          <span>子代理输出</span>
        </div>
        <pre
          class="terminal-task-pre"
          :class="{ 'terminal-task-pre--error': entry.hasErrorOutput }"
          >{{ entry.outputText }}</pre
        >
      </div>
      <div v-if="entry.pending && isSessionRunning" class="terminal-task-pending">
        <span class="terminal-blink">█</span>
      </div>
    </div>
  </div>
</template>
