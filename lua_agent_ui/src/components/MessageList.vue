<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { AgentName, Message } from '../types'
import AgentMessage from './AgentMessage.vue'

const props = defineProps<{
  messages: Message[]
  isProcessing?: boolean
  activeAgent?: AgentName | null
  processingStartedAt?: Date | null
}>()

const now = ref(Date.now())
let timerId: number | null = null

const thinkingStep = computed(() => {
  if (props.activeAgent === 'clarifier') return 'Уточняю детали задачи'
  if (props.activeAgent === 'planner') return 'Анализирую запрос'
  if (props.activeAgent === 'coder') return 'Пишу решение'
  if (props.activeAgent === 'validator') return 'Проверяю результат'
  return 'Размышляю над задачей'
})

const elapsedLabel = computed(() => {
  if (!props.processingStartedAt) return '0м 00с'
  const elapsedMs = Math.max(0, now.value - props.processingStartedAt.getTime())
  const totalSeconds = Math.floor(elapsedMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}м ${seconds.toString().padStart(2, '0')}с`
})

function startTimer() {
  if (timerId !== null) return
  timerId = window.setInterval(() => {
    now.value = Date.now()
  }, 1000)
}

function stopTimer() {
  if (timerId === null) return
  window.clearInterval(timerId)
  timerId = null
}

watch(
  () => props.isProcessing,
  (processing) => {
    if (processing) startTimer()
    else stopTimer()
  },
  { immediate: true },
)

onMounted(() => {
  if (props.isProcessing) startTimer()
})

onBeforeUnmount(() => {
  stopTimer()
})

function userPlainText(m: Message): string {
  return m.content
    .filter((c) => c.type === 'text' && c.text)
    .map((c) => c.text)
    .join('\n')
}
</script>

<template>
  <div class="mx-auto w-full max-w-composer py-6">
    <template v-for="m in messages" :key="m.id">
      <div v-if="m.role === 'user'" class="mb-6 text-right">
        <div
          class="inline-block max-w-[90%] rounded-[20px] bg-chat-active px-4 py-3 text-left text-[14px] text-ink"
        >
          {{ userPlainText(m) }}
        </div>
      </div>
      <div v-else class="mb-8">
        <AgentMessage :message="m" />
      </div>
    </template>
    <div
      v-if="props.isProcessing"
      class="mb-8 rounded-[20px] bg-surface p-4 text-left md:p-5"
    >
      <p class="text-[16px] font-bold text-black">Идёт обработка</p>
      <p class="mt-1 text-[14px] text-ink-secondary">
        {{ thinkingStep }}<span class="animate-pulse">...</span>
      </p>
      <p class="mt-1 text-[13px] text-ink-muted">Прошло времени: {{ elapsedLabel }}</p>
    </div>
  </div>
</template>
