<script setup lang="ts">
import ChatRichTextRenderer from "../../chat/ChatRichTextRenderer.vue";
import type { AgentMessage } from "../../../types/api";

defineProps<{
  message: AgentMessage;
}>();
</script>

<template>
  <div class="chat-ai-final bubble-other">
    <ChatRichTextRenderer :content="message.content || ''" />
  </div>
</template>
