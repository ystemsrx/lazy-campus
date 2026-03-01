<script setup lang="ts">
import { computed } from "vue";
import type { TerminalEntry } from "../../agentViewTypes";
import { parseSearchResults } from "../../agentViewUtils";

const props = defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();

const results = computed(() => parseSearchResults(props.entry.outputText));
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--search-web">
      <div class="terminal-tool-head terminal-tool-head--search-web">
        <i class="fa-solid fa-globe"></i>
        <span>SearchWeb</span>
      </div>
      <div class="terminal-tool-detail">
        <span class="terminal-tool-key">query</span>
        <span class="terminal-tool-val terminal-tool-val--highlight">{{
          entry.args?.query
        }}</span>
      </div>
      <template v-if="!entry.pending && entry.outputText">
        <div v-if="results.length" class="terminal-tool-body">
          <div
            v-for="(result, idx) in results"
            :key="idx"
            class="terminal-search-item"
          >
            <div class="terminal-search-title">
              <i class="fa-solid fa-arrow-up-right-from-square"></i>
              <a
                v-if="result.url"
                :href="result.url"
                target="_blank"
                rel="noopener"
                >{{ result.title || result.url }}</a
              >
              <span v-else>{{ result.title }}</span>
            </div>
            <div v-if="result.url" class="terminal-search-url">
              {{ result.url }}
            </div>
            <div v-if="result.summary" class="terminal-search-summary">
              {{ result.summary }}
            </div>
          </div>
        </div>
        <pre
          v-else
          class="terminal-pre terminal-pre--incard"
          :class="{
            'terminal-pre--error': entry.hasErrorOutput,
          }"
          >{{ entry.outputText }}</pre
        >
      </template>
    </div>
    <div v-if="entry.pending && isSessionRunning" class="terminal-status">
      <span class="terminal-blink">█</span>
    </div>
  </div>
</template>
