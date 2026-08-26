<script setup lang="ts">
import type { AgentName, Message } from '../types'
import ChatGreetingBlock from './ChatGreetingBlock.vue'
import ChatInput from './ChatInput.vue'
import MessageList from './MessageList.vue'

const props = defineProps<{
  messages: Message[]
  disabled?: boolean
  isProcessing?: boolean
  activeAgent?: AgentName | null
  processingStartedAt?: Date | null
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
}>()
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col bg-page">
    <template v-if="props.messages.length === 0">
      <div
        class="flex min-h-0 flex-1 flex-col items-center justify-center px-6 md:px-10"
      >
        <ChatGreetingBlock>
          <ChatInput variant="welcome" :disabled="disabled" @send="emit('send', $event)" />
        </ChatGreetingBlock>
      </div>
    </template>
    <template v-else>
      <div class="min-h-0 flex-1 overflow-y-auto">
        <MessageList
          :messages="messages"
          :is-processing="props.isProcessing"
          :active-agent="props.activeAgent"
          :processing-started-at="props.processingStartedAt"
        />
      </div>
      <div class="flex shrink-0 justify-center bg-page px-6 pb-6 pt-2 md:px-10">
        <ChatInput variant="chat" :disabled="disabled" @send="emit('send', $event)" />
      </div>
    </template>
  </div>
</template>
