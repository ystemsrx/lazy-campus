<script setup lang="ts">
import type { TerminalEntry } from "../../agentViewTypes";

defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--glob">
      <div class="terminal-tool-head terminal-tool-head--glob">
        <i class="fa-solid fa-folder-tree"></i>
        <span>Glob</span>
      </div>
      <div class="terminal-tool-detail">
        <span class="terminal-tool-key">pattern</span>
        <span class="terminal-tool-val terminal-tool-val--highlight">{{
          entry.args?.pattern
        }}</span>
      </div>
      <div v-if="!entry.pending && entry.outputText" class="terminal-tool-body">
        <template v-for="(line, idx) in entry.outputText.split('\n')" :key="idx">
          <div
            v-if="line.trim()"
            :class="
              /^Found \d|^No match/i.test(line)
                ? 'terminal-tool-info'
                : 'terminal-tool-file'
            "
          >
            <i
              :class="
                /^Found \d|^No match/i.test(line)
                  ? 'fa-solid fa-circle-info'
                  : 'fa-regular fa-file-code'
              "
            ></i>
            <span>{{ line }}</span>
          </div>
        </template>
      </div>
    </div>
    <div v-if="entry.pending && isSessionRunning" class="terminal-status">
      <span class="terminal-blink">█</span>
    </div>
  </div>
</template>
