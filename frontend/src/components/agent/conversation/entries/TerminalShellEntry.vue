<script setup lang="ts">
import type { TerminalEntry } from "../../agentViewTypes";
import {
  TERMINAL_DEFAULT_CWD,
  isExitCodeSystemErrorLine,
  startsWithErrorPrefix,
} from "../../agentViewUtils";

defineProps<{
  entry: TerminalEntry;
  terminalHostname: string;
  isSessionRunning: boolean;
}>();
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-prompt-line">
      <span
        v-if="entry.success === false"
        class="terminal-status-icon terminal-status-icon--err"
        ><i class="fa-solid fa-xmark"></i
      ></span>
      <span class="terminal-user">{{ terminalHostname }}</span
      >:<span class="terminal-path">{{
        entry.promptPath || TERMINAL_DEFAULT_CWD
      }}</span
      ><span class="terminal-dollar">$</span>
      <span class="terminal-cmd">{{ entry.command }}</span>
    </div>
    <div
      v-for="(line, idx) in entry.systemLines"
      :key="'s' + idx"
      class="terminal-sys-line"
      :class="{
        'terminal-sys-line--error':
          startsWithErrorPrefix(line) || isExitCodeSystemErrorLine(line),
      }"
    >
      {{ line }}
    </div>
    <pre
      v-if="entry.outputText"
      class="terminal-pre"
      :class="{ 'terminal-pre--error': entry.hasErrorOutput }"
      >{{ entry.outputText }}</pre
    >
    <div v-if="entry.pending && isSessionRunning" class="terminal-status">
      <span class="terminal-blink">█</span>
    </div>
  </div>
</template>
