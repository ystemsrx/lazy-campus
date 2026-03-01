<script setup lang="ts">
import { computed } from "vue";
import type { TerminalEntry } from "../../agentViewTypes";
import { buildStrReplaceDiffLines, getStrReplaceEdits } from "../../agentViewUtils";

const props = defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();

const edits = computed(() => getStrReplaceEdits(props.entry.args));
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--str-replace">
      <div class="terminal-tool-head terminal-tool-head--str-replace">
        <i class="fa-solid fa-pen-to-square"></i>
        <span>StrReplaceFile</span>
      </div>
      <div class="terminal-tool-detail">
        <span class="terminal-tool-key">path</span>
        <span class="terminal-tool-val">{{ entry.filePath }}</span>
      </div>
      <div v-if="edits.length" class="terminal-diff">
        <div class="terminal-diff-meta">
          --- a/{{ entry.filePath || "(unknown)" }}
        </div>
        <div class="terminal-diff-meta">
          +++ b/{{ entry.filePath || "(unknown)" }}
        </div>
        <template v-for="(edit, editIdx) in edits" :key="`edit-${editIdx}`">
          <div class="terminal-diff-hunk">@@ edit {{ editIdx + 1 }} @@</div>
          <div
            v-for="(line, lineIdx) in buildStrReplaceDiffLines(edit)"
            :key="`line-${editIdx}-${lineIdx}`"
            class="terminal-diff-line"
            :class="
              line.kind === 'old'
                ? 'terminal-diff-line--old'
                : 'terminal-diff-line--new'
            "
          >
            <span class="terminal-diff-line-prefix">{{
              line.kind === "old" ? "-" : "+"
            }}</span>
            <code class="terminal-diff-line-code">{{ line.text || " " }}</code>
          </div>
        </template>
      </div>
      <div
        v-if="!entry.pending && entry.outputText"
        class="terminal-tool-ok-line"
        :class="{
          'terminal-tool-ok-line--error': entry.hasErrorOutput,
        }"
      >
        <i
          :class="
            entry.hasErrorOutput ? 'fa-solid fa-xmark' : 'fa-solid fa-check'
          "
        ></i>
        {{ entry.outputText }}
      </div>
    </div>
    <div v-if="entry.pending && isSessionRunning" class="terminal-status">
      <span class="terminal-blink">█</span>
    </div>
  </div>
</template>
