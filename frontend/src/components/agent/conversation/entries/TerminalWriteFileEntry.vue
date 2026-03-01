<script setup lang="ts">
import { computed } from "vue";
import type { TerminalEntry } from "../../agentViewTypes";
import { formatReadFileContent, startsWithErrorPrefix } from "../../agentViewUtils";

const props = defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();

const hasWriteContent = computed(() =>
  Object.prototype.hasOwnProperty.call(props.entry.args ?? {}, "content"),
);

const writeContent = computed(() => {
  const raw = props.entry.args?.content;
  if (raw == null) return "";
  if (typeof raw === "string") return raw;
  try {
    return JSON.stringify(raw, null, 2);
  } catch {
    return String(raw);
  }
});
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-write-box">
      <div class="terminal-write-head">
        <i class="fa-solid fa-file-pen"></i>
        <span>WriteFile</span>
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
      <div v-if="hasWriteContent" class="terminal-readfile-output">
        <div class="terminal-readfile-output-label">
          <i class="fa-solid fa-align-left"></i>
          <span>写入内容</span>
        </div>
        <pre class="terminal-readfile-pre">{{
          formatReadFileContent(writeContent)
        }}</pre>
      </div>
      <div v-else-if="entry.outputText" class="terminal-readfile-output">
        <div class="terminal-readfile-output-label">
          <i class="fa-solid fa-align-left"></i>
          <span>工具输出</span>
        </div>
        <pre
          class="terminal-readfile-pre"
          :class="{
            'terminal-readfile-pre--error': entry.hasErrorOutput,
          }"
          >{{ entry.outputText }}</pre
        >
      </div>
      <div v-if="entry.pending && isSessionRunning" class="terminal-task-pending">
        <span class="terminal-blink">█</span>
      </div>
    </div>
  </div>
</template>
