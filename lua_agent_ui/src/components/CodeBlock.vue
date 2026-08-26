<script setup lang="ts">
import hljs from 'highlight.js/lib/core'
import json from 'highlight.js/lib/languages/json'
import lua from 'highlight.js/lib/languages/lua'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import TextSelectionPopup from './TextSelectionPopup.vue'

hljs.registerLanguage('lua', lua)
hljs.registerLanguage('json', json)

const props = defineProps<{
  code: string
  language?: string
}>()

const rootRef = ref<HTMLElement | null>(null)
const popupVisible = ref(false)
const popupX = ref(0)
const popupY = ref(0)

const highlighted = computed(() => {
  const language = props.language === 'json' ? 'json' : 'lua'
  try {
    return hljs.highlight(props.code, { language }).value
  } catch {
    return props.code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
  }
})

function onMouseUp() {
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed || !rootRef.value) {
    popupVisible.value = false
    return
  }
  const anchor = sel.anchorNode
  if (!anchor || !rootRef.value.contains(anchor)) {
    popupVisible.value = false
    return
  }
  const range = sel.getRangeAt(0)
  const rect = range.getBoundingClientRect()
  if (rect.width < 2 && rect.height < 2) {
    popupVisible.value = false
    return
  }
  popupX.value = Math.min(rect.left, window.innerWidth - 220)
  popupY.value = Math.max(8, rect.top - 40)
  popupVisible.value = true
}

function onDocMouseDown(ev: MouseEvent) {
  const t = ev.target as Node
  if (rootRef.value?.contains(t)) return
  popupVisible.value = false
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(props.code)
  } catch {
    /* без toast по ТЗ */
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onDocMouseDown)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocMouseDown)
})
</script>

<template>
  <div
    ref="rootRef"
    class="mb-[12px] overflow-hidden rounded-[10px] border border-border bg-surface"
    @mouseup="onMouseUp"
  >
    <div
      class="flex items-center justify-between border-b border-border px-[14px] py-[8px]"
    >
      <span class="text-[13px] font-medium text-ink-secondary">{{ language ?? 'Lua' }}</span>
      <button
        type="button"
        class="cursor-pointer text-ink-muted transition-opacity hover:opacity-70"
        aria-label="Копировать"
        @click="copyCode"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      </button>
    </div>
    <pre
      class="m-0 overflow-x-auto bg-codebg p-[14px] font-mono text-[13px] leading-relaxed text-ink"
    ><code class="language-lua hljs-lua-custom" v-html="highlighted" /></pre>
    <TextSelectionPopup
      :visible="popupVisible"
      :x="popupX"
      :y="popupY"
      @action="popupVisible = false"
    />
  </div>
</template>

<style scoped>
:deep(.hljs-lua-custom .hljs-keyword),
:deep(.hljs-lua-custom .hljs-built_in),
:deep(.hljs-lua-custom .hljs-literal) {
  color: var(--color-code-keyword);
}
:deep(.hljs-lua-custom .hljs-string) {
  color: var(--color-code-string);
}
:deep(.hljs-lua-custom .hljs-comment) {
  color: var(--color-code-comment);
}
:deep(.hljs-lua-custom .hljs-number) {
  color: var(--color-code-number);
}
</style>
