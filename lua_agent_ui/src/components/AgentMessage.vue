<script setup lang="ts">
import type { Message, MessageContent } from '../types'
import CodeBlock from './CodeBlock.vue'
import DiffBlock from './DiffBlock.vue'

defineProps<{
  message: Message
}>()

type Group =
  | { kind: 'texts'; items: MessageContent[] }
  | { kind: 'code'; block: MessageContent }
  | { kind: 'diff'; block: MessageContent }

function buildGroups(content: MessageContent[]): Group[] {
  const groups: Group[] = []
  let i = 0
  while (i < content.length) {
    if (content[i].type === 'text') {
      const texts: MessageContent[] = []
      while (i < content.length && content[i].type === 'text') {
        texts.push(content[i])
        i++
      }
      groups.push({ kind: 'texts', items: texts })
      continue
    }
    if (content[i].type === 'code') {
      groups.push({ kind: 'code', block: content[i] })
      i++
      continue
    }
    if (content[i].type === 'diff') {
      groups.push({ kind: 'diff', block: content[i] })
      i++
      continue
    }
    i++
  }
  return groups
}
</script>

<template>
  <div
    class="rounded-[20px] bg-surface p-4 text-left md:p-5"
  >
    <template v-for="(g, gi) in buildGroups(message.content)" :key="gi">
      <template v-if="g.kind === 'texts'">
        <p
          v-for="(t, ti) in g.items"
          :key="ti"
          class="mb-2 leading-relaxed"
          :class="
            ti === 0
              ? 'text-[16px] font-bold text-black'
              : 'text-[14px] text-ink-secondary'
          "
        >
          {{ t.text }}
        </p>
      </template>
      <CodeBlock
        v-else-if="g.kind === 'code' && g.block.code"
        :code="g.block.code"
        :language="g.block.language"
      />
      <DiffBlock
        v-else-if="g.kind === 'diff' && g.block.diffOld != null && g.block.diffNew != null"
        :diff-old="g.block.diffOld"
        :diff-new="g.block.diffNew"
        :total-lines="g.block.totalLines"
      />
    </template>
  </div>
</template>
