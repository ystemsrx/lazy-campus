<script setup lang="ts">
import type { Component } from "vue";
import type { TerminalEntry } from "../agentViewTypes";
import TerminalFetchUrlEntry from "./entries/TerminalFetchUrlEntry.vue";
import TerminalGlobEntry from "./entries/TerminalGlobEntry.vue";
import TerminalGrepEntry from "./entries/TerminalGrepEntry.vue";
import TerminalReadFileEntry from "./entries/TerminalReadFileEntry.vue";
import TerminalReadMediaEntry from "./entries/TerminalReadMediaEntry.vue";
import TerminalSearchWebEntry from "./entries/TerminalSearchWebEntry.vue";
import TerminalSetTodoEntry from "./entries/TerminalSetTodoEntry.vue";
import TerminalShellEntry from "./entries/TerminalShellEntry.vue";
import TerminalStrReplaceEntry from "./entries/TerminalStrReplaceEntry.vue";
import TerminalTaskEntry from "./entries/TerminalTaskEntry.vue";
import TerminalWriteFileEntry from "./entries/TerminalWriteFileEntry.vue";

const props = defineProps<{
  roundId: number;
  entries: TerminalEntry[];
  terminalHostname: string;
  isSessionRunning: boolean;
}>();

const emit = defineEmits<{
  (e: "terminal-scroll", payload: { event: Event; roundId: number }): void;
}>();

const entryComponentMap: Partial<
  Record<TerminalEntry["toolType"], Component>
> = {
  shell: TerminalShellEntry,
  "write-file": TerminalWriteFileEntry,
  "read-file": TerminalReadFileEntry,
  glob: TerminalGlobEntry,
  grep: TerminalGrepEntry,
  "search-web": TerminalSearchWebEntry,
  "fetch-url": TerminalFetchUrlEntry,
  "set-todo": TerminalSetTodoEntry,
  task: TerminalTaskEntry,
  "str-replace": TerminalStrReplaceEntry,
  "read-media": TerminalReadMediaEntry,
};

function getEntryProps(entry: TerminalEntry): Record<string, unknown> {
  if (entry.toolType === "shell") {
    return {
      entry,
      terminalHostname: props.terminalHostname,
      isSessionRunning: props.isSessionRunning,
    };
  }
  return {
    entry,
    isSessionRunning: props.isSessionRunning,
  };
}
</script>

<template>
  <div class="terminal">
    <div class="terminal-titlebar">
      <div class="terminal-dots">
        <span class="terminal-dot terminal-dot--red"></span>
        <span class="terminal-dot terminal-dot--yellow"></span>
        <span class="terminal-dot terminal-dot--green"></span>
      </div>
      <span class="terminal-hostname">{{ terminalHostname }}</span>
    </div>
    <div
      class="terminal-body"
      :data-round-id="roundId"
      @scroll="emit('terminal-scroll', { event: $event, roundId })"
    >
      <template v-for="entry in entries" :key="entry.id">
        <component
          :is="entryComponentMap[entry.toolType]"
          v-if="entryComponentMap[entry.toolType]"
          v-bind="getEntryProps(entry)"
        />

        <div v-else class="terminal-entry">
          <div class="terminal-other-line">
            <span class="terminal-other-icon">⚙</span>
            <span class="terminal-other-name">{{ entry.toolName }}</span>
          </div>
          <pre v-if="entry.rawArgs" class="terminal-pre terminal-pre--args">{{
            entry.rawArgs
          }}</pre>
          <div
            v-for="(line, idx) in entry.systemLines"
            :key="'s' + idx"
            class="terminal-sys-line"
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
    </div>
  </div>
</template>
