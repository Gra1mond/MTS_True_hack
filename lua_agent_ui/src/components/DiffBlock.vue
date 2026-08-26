<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  diffOld: string
  diffNew: string
  totalLines?: number
}>()

const oldLines = computed(() => props.diffOld.split('\n'))
const newLines = computed(() => props.diffNew.split('\n'))
</script>

<template>
  <div class="mb-[12px] overflow-hidden rounded-[10px] border border-border bg-surface">
    <div
      class="flex items-center justify-between border-b border-border px-[14px] py-[8px]"
    >
      <span class="text-[13px] font-medium text-ink-secondary">Lua</span>
    </div>
    <div class="bg-codebg p-[14px] font-mono text-[13px] text-ink">
      <div
        v-for="(line, i) in oldLines"
        :key="'o' + i"
        class="whitespace-pre-wrap px-1 py-0.5"
        style="background-color: var(--color-diff-red-bg)"
      >
        {{ line || ' ' }}
      </div>
      <div
        v-for="(line, i) in newLines"
        :key="'n' + i"
        class="whitespace-pre-wrap px-1 py-0.5"
        style="background-color: var(--color-diff-green-bg)"
      >
        {{ line || ' ' }}
      </div>
    </div>
    <div
      class="flex items-center justify-between border-t border-border px-[14px] py-[8px] text-ink-secondary"
    >
      <span class="text-[13px]">Внести изменения?</span>
      <div class="flex items-center gap-3">
        <button type="button" class="cursor-pointer" aria-label="Подтвердить">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </button>
        <button type="button" class="cursor-pointer" aria-label="Отменить">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  </div>

  <div
    class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-[14px] py-[10px] text-[13px]"
  >
    <span>Внести все изменения? ({{ totalLines ?? 200 }} строк)</span>
    <div class="flex gap-4 font-medium text-accent">
      <button type="button" class="cursor-pointer">Да</button>
      <button type="button" class="cursor-pointer">Нет</button>
    </div>
  </div>
</template>
