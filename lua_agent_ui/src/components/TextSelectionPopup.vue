<script setup lang="ts">
defineProps<{
  visible: boolean
  x: number
  y: number
}>()

const emit = defineEmits<{
  (e: 'action'): void
}>()
</script>

<template>
  <div
    v-show="visible"
    class="fixed z-50 flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-surface px-[12px] py-[6px] shadow-[0_2px_8px_rgba(0,0,0,0.1)]"
    :style="{ left: `${x}px`, top: `${y}px` }"
    role="button"
    tabindex="0"
    @mousedown.prevent
    @click="emit('action')"
  >
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
    <span class="text-[13px] text-ink-secondary">Спросить у LocalScript</span>
  </div>
</template>
