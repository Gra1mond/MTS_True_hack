<script setup lang="ts">
import ChatGreetingBlock from './ChatGreetingBlock.vue'
import ChatInput from './ChatInput.vue'

const emit = defineEmits<{
  (e: 'send', text: string): void
}>()

defineProps<{
  disabled?: boolean
}>()
</script>

<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col items-center justify-center bg-page px-6 md:px-10"
  >
    <ChatGreetingBlock>
      <ChatInput variant="welcome" :disabled="disabled" @send="emit('send', $event)" />
    </ChatGreetingBlock>
  </div>
</template>
