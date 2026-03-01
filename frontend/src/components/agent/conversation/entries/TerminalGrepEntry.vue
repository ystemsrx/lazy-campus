<script setup lang="ts">
import type { TerminalEntry } from "../../agentViewTypes";

defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--grep">
      <div class="terminal-tool-head terminal-tool-head--grep">
        <i class="fa-solid fa-magnifying-glass-code"></i>
        <span>Grep</span>
      </div>
      <div class="terminal-tool-detail">
        <span class="terminal-tool-key">pattern</span>
        <span class="terminal-tool-val terminal-tool-val--highlight">{{
          entry.args?.pattern
        }}</span>
      </div>
      <div v-if="entry.args?.path" class="terminal-tool-detail">
        <span class="terminal-tool-key">path</span>
        <span class="terminal-tool-val">{{ entry.args.path }}</span>
      </div>
      <div v-if="entry.args?.output_mode" class="terminal-tool-detail">
        <span class="terminal-tool-key">mode</span>
        <span class="terminal-tool-val">{{ entry.args.output_mode }}</span>
      </div>
      <div v-if="!entry.pending && entry.outputText" class="terminal-tool-body">
        <template v-for="(line, idx) in entry.outputText.split('\n')" :key="idx">
          <div
            v-if="line.trim()"
            :class="
              /^No match/i.test(line) ? 'terminal-tool-info' : 'terminal-tool-file'
            "
          >
            <i
              :class="
                /^No match/i.test(line)
                  ? 'fa-solid fa-circle-info'
                  : 'fa-solid fa-font'
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
