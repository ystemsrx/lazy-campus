<script setup lang="ts">
import { computed } from "vue";
import type { TerminalEntry } from "../../agentViewTypes";
import { parseFetchResult } from "../../agentViewUtils";

const props = defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();

const fetchData = computed(() => parseFetchResult(props.entry.outputText));
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--fetch-url">
      <div class="terminal-tool-head terminal-tool-head--fetch-url">
        <i class="fa-solid fa-link"></i>
        <span>FetchURL</span>
      </div>
      <div class="terminal-tool-detail">
        <span class="terminal-tool-key">url</span>
        <a
          class="terminal-tool-link"
          :href="entry.args?.url"
          target="_blank"
          rel="noopener"
          >{{ entry.args?.url }}</a
        >
      </div>
      <template v-if="!entry.pending && entry.outputText">
        <div v-if="fetchData" class="terminal-fetch-preview">
          <div v-if="fetchData.title" class="terminal-fetch-title">
            {{ fetchData.title }}
          </div>
          <div v-if="fetchData.content" class="terminal-fetch-content">
            {{ fetchData.content }}
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
