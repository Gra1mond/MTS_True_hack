<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  variant: 'welcome' | 'chat'
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
}>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const MIN_TEXTAREA_HEIGHT = 24
const MAX_TEXTAREA_HEIGHT = 96

function submit() {
  if (props.disabled) return
  const t = text.value.trim()
  if (!t) return
  emit('send', t)
  text.value = ''
  nextTick(resizeTextarea)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

function resizeTextarea() {
  const el = textareaRef.value
  if (!el) return

  el.style.height = 'auto'
  const nextHeight = Math.min(MAX_TEXTAREA_HEIGHT, Math.max(MIN_TEXTAREA_HEIGHT, el.scrollHeight))
  el.style.height = `${nextHeight}px`
  el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_HEIGHT ? 'auto' : 'hidden'
}

onMounted(() => {
  resizeTextarea()
})

watch(text, () => {
  nextTick(resizeTextarea)
})
</script>

<template>
  <div class="w-full max-w-[802px]">
    <div
      class="relative isolate box-border h-auto min-h-[92px] max-h-[180px] w-full overflow-hidden rounded-[28px] border-2 border-black bg-surface [contain:paint]"
    >
      <textarea
        ref="textareaRef"
        v-model="text"
        :disabled="disabled"
        :placeholder="variant === 'welcome' ? 'Напишите запрос…' : 'Спросить у LocalScript'"
        class="block min-h-[24px] w-full resize-none border-0 bg-transparent px-[32px] pb-[14px] pr-[76px] pt-[14px] text-[16pt] text-ink placeholder:text-[16pt] placeholder:text-ink-secondary placeholder:opacity-100 focus:outline-none focus:ring-0 disabled:opacity-50 [font-family:var(--font-display)] [clip-path:inset(0_round_26px)]"
        @keydown="onKeydown"
      />
      <button
        type="button"
        :disabled="disabled || !text.trim()"
        class="absolute right-[22px] top-[14px] flex h-9 w-9 items-center justify-center rounded-full text-accent transition hover:bg-black/[0.04] hover:opacity-80 disabled:opacity-40"
        aria-label="Отправить"
        @click="submit"
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.9"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M22 2 11 13" />
          <path d="M22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
  </div>
</template>
