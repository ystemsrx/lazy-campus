<script setup lang="ts">
import ChatRichTextRenderer from "../../chat/ChatRichTextRenderer.vue";
import { getFileIconComponent } from "../../../composables/chat/attachmentUtils";
import type { AgentMessage } from "../../../types/api";
import { formatFileSize } from "../agentViewUtils";

defineProps<{
  message: AgentMessage;
}>();

function getAgentFileIcon(name: string, mime = "") {
  return getFileIconComponent(mime, name);
}
</script>

<template>
  <div class="chat-bubble-row chat-bubble-row--right">
    <div class="chat-bubble chat-bubble--user">
      <ChatRichTextRenderer :content="message.content || ''" />
      <div v-if="message.attachments?.length" class="chat-bubble-files">
        <span
          v-for="att in message.attachments"
          :key="att.stored_name"
          class="chat-file-chip"
        >
          <component
            :is="getAgentFileIcon(att.name)"
            :size="14"
            class="agent-file-icon"
          />
          {{ att.name }}
          <small>({{ formatFileSize(att.size) }})</small>
        </span>
      </div>
    </div>
  </div>
</template>
