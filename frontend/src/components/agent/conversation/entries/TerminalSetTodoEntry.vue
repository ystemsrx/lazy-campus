<script setup lang="ts">
import type { TerminalEntry } from "../../agentViewTypes";

defineProps<{
  entry: TerminalEntry;
  isSessionRunning: boolean;
}>();
</script>

<template>
  <div class="terminal-entry">
    <div class="terminal-tool-box terminal-tool-box--todo">
      <div class="terminal-tool-head terminal-tool-head--todo">
        <i class="fa-solid fa-list-check"></i>
        <span>SetTodoList</span>
      </div>
      <div v-if="entry.args?.todos?.length" class="terminal-todo-list">
        <div
          v-for="(todo, idx) in entry.args.todos"
          :key="idx"
          class="terminal-todo-item"
        >
          <i
            :class="
              todo.status === 'done'
                ? 'fa-solid fa-circle-check terminal-todo--done'
                : todo.status === 'in_progress'
                  ? 'fa-solid fa-circle-dot terminal-todo--progress'
                  : 'fa-regular fa-circle terminal-todo--pending'
            "
          ></i>
          <span
            class="terminal-todo-title"
            :class="{
              'terminal-todo-title--done': todo.status === 'done',
            }"
            >{{ todo.title }}</span
          >
          <span
            class="terminal-todo-badge"
            :class="'terminal-todo-badge--' + (todo.status || 'pending')"
            >{{ todo.status }}</span
          >
        </div>
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
