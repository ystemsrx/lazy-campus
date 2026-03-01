<script setup lang="ts">
import type { TerminalEntry } from "../../agentViewTypes";
import { startsWithErrorPrefix } from "../../agentViewUtils";

defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-write-box terminal-write-box--read">
      <div class="terminal-write-head terminal-write-head--read">
        <i class="fa-solid fa-file-lines"></i>
        <span>ReadFile</span>
      </div>
      <div class="terminal-write-detail">
        <span class="terminal-write-key">path</span>
        <span class="terminal-write-val">{{ entry.filePath }}</span>
      </div>
      <div
        v-for="(line, idx) in entry.systemLines"
        :key="'s' + idx"
        class="terminal-write-ok"
        :class="{
          'terminal-write-ok--error':
            startsWithErrorPrefix(line) || entry.hasErrorOutput,
        }"
      >
        <i
          :class="
            startsWithErrorPrefix(line) || entry.hasErrorOutput
              ? 'fa-solid fa-xmark'
              : 'fa-solid fa-check'
          "
        ></i>
        {{ line }}
      </div>
      <div v-if="entry.pending && isSessionRunning" class="terminal-task-pending">
        <span class="terminal-blink">█</span>
      </div>
    </div>
  </div>
</template>
