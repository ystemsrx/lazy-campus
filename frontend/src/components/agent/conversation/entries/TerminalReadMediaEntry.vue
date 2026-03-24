<script setup lang="ts">
import { computed } from "vue";
import type { TerminalEntry } from "../../agentViewTypes";
import { parseMediaOutput } from "../../agentViewUtils";

const props = defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();

const media = computed(() =>
  parseMediaOutput(
    [...(props.entry.systemLines || []), props.entry.outputText || ""].join("\n"),
  ),
);
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--read-media">
      <div class="terminal-tool-head terminal-tool-head--read-media">
        <i class="fa-solid fa-image"></i>
        <span>ReadMediaFile</span>
      </div>
      <div class="terminal-tool-detail">
        <i
          v-if="
            !entry.pending &&
            !entry.hasErrorOutput &&
            (entry.outputText || entry.systemLines.length)
          "
          class="fa-solid fa-check terminal-readmedia-path-ok"
        ></i>
        <span class="terminal-tool-key">path</span>
        <span class="terminal-tool-val">{{ entry.filePath }}</span>
      </div>
      <div
        v-if="
          !entry.pending &&
          (entry.outputText || entry.systemLines.length) &&
          (media.prettyDimensions || media.format || media.size)
        "
        class="terminal-media-preview"
      >
        <div class="terminal-media-meta">
          <div
            v-if="media.prettyDimensions"
            class="terminal-media-chip terminal-media-chip--spec"
          >
            <i class="fa-solid fa-expand"></i>
            <span>{{ media.prettyDimensions }}</span>
          </div>
          <div v-if="media.format" class="terminal-media-chip">
            <i class="fa-solid fa-file-image"></i>
            <span>{{ media.format }}</span>
          </div>
          <div v-if="media.size" class="terminal-media-chip">
            <i class="fa-solid fa-weight-hanging"></i>
            <span>{{ media.size }}</span>
          </div>
        </div>
      </div>
      <pre
        v-if="!entry.pending && entry.outputText && !media.shouldHideRawOutput"
        class="terminal-pre terminal-pre--incard"
        :class="{
          'terminal-pre--error': entry.hasErrorOutput,
        }"
        >{{ entry.outputText }}</pre
      >
      <div v-if="entry.pending && isSessionRunning" class="terminal-task-pending">
        <span class="terminal-blink">█</span>
      </div>
    </div>
  </div>
</template>
