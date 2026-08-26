<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'

defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void
}>()

const store = useChatStore()
const router = useRouter()
const { chats, activeChatId } = storeToRefs(store)
const isSearchOpen = ref(false)
const searchQuery = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)
const searchControlsRef = ref<HTMLElement | null>(null)

const filteredChats = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return chats.value
  return chats.value.filter((chat) => chat.title.toLowerCase().includes(query))
})

function selectChat(id: string) {
  store.setActiveChat(id)
  void router.push('/')
}

function onNewChat() {
  store.newEmptyChat()
  void router.push('/')
}

function openSettings() {
  void router.push('/settings')
}

function toggleSearch() {
  isSearchOpen.value = !isSearchOpen.value
  if (!isSearchOpen.value) {
    searchQuery.value = ''
    return
  }
  nextTick(() => {
    searchInputRef.value?.focus()
  })
}

function closeSearch() {
  isSearchOpen.value = false
  searchQuery.value = ''
}

function onDocumentMouseDown(event: MouseEvent) {
  if (!isSearchOpen.value) return
  const target = event.target as Node | null
  if (!target) return
  if (searchControlsRef.value?.contains(target)) return
  closeSearch()
}

onMounted(() => {
  document.addEventListener('mousedown', onDocumentMouseDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocumentMouseDown)
})

function deleteChat(id: string, ev: Event) {
  ev.stopPropagation()
  store.deleteChat(id)
}
</script>

<template>
  <aside
    class="relative flex h-full shrink-0 flex-col bg-sidebar transition-[width,min-width] duration-200 ease-out"
    :class="collapsed ? 'w-sidebar-collapsed min-w-sidebar-collapsed overflow-hidden' : 'w-sidebar min-w-sidebar'"
  >
    <template v-if="collapsed">
      <div class="flex flex-1 flex-col items-center pt-5">
        <button
          type="button"
          class="rounded-lg p-1 text-icon-header transition hover:bg-black/[0.06]"
          aria-label="Развернуть панель"
          @click="emit('toggle-sidebar')"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
    </template>

    <template v-else>
      <div class="shrink-0">
        <div
          ref="searchControlsRef"
          class="flex h-[56px] items-center gap-2 pl-[16px] pr-[14px]"
        >
          <div class="flex h-9 w-9 shrink-0 items-center justify-center">
            <button
              type="button"
              class="flex h-9 w-9 items-center justify-center rounded-lg text-icon-header transition hover:bg-black/[0.06]"
              aria-label="Свернуть панель"
              @click="emit('toggle-sidebar')"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          </div>
          <div
            class="min-w-0 overflow-hidden transition-all duration-200 ease-out"
            :class="isSearchOpen ? 'flex-1 opacity-100' : 'flex-1 opacity-0'"
          >
            <input
              v-if="isSearchOpen"
              ref="searchInputRef"
              v-model="searchQuery"
              type="text"
              placeholder="Поиск чатов"
              class="h-9 w-full rounded-lg border border-border bg-surface px-3 text-[13px] text-ink placeholder:text-ink-muted focus:outline-none"
            />
            <div v-else class="h-9" />
          </div>
          <button
            type="button"
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-icon-header transition hover:bg-black/[0.06]"
            aria-label="Поиск"
            @click="toggleSearch"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </button>
        </div>
        <div class="pb-[10px] pt-[2px]">
          <button
            type="button"
            class="flex w-full items-center gap-2 rounded-lg py-2 pl-[16px] pr-[14px] text-left text-[14px] text-ink transition hover:bg-black/[0.04] [font-family:var(--font-display)]"
            @click="onNewChat"
          >
            <span class="flex h-9 w-9 shrink-0 items-center justify-center">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </span>
            <span class="min-w-0 truncate">Новый чат</span>
          </button>
        </div>
      </div>

      <div class="px-[16px] pb-[4px] pt-[12px] text-[14px] text-black [font-family:var(--font-display)]">
        Чаты
      </div>

      <ul class="min-h-0 flex-1 overflow-y-auto px-[8px] pb-[8px]">
        <li v-for="c in filteredChats" :key="c.id">
          <div
            class="group flex w-full items-center gap-1 rounded-lg px-[8px] py-[4px] transition-colors"
            :class="activeChatId === c.id ? 'bg-chat-active' : ''"
          >
            <button
              type="button"
              class="min-w-0 flex-1 rounded-md px-[8px] py-[8px] text-left text-[14px] font-medium text-ink transition-colors"
              :class="activeChatId === c.id ? 'font-medium' : ''"
              @click="selectChat(c.id)"
            >
              <span class="line-clamp-2">{{ c.title }}</span>
            </button>
            <button
              type="button"
              class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-ink-secondary opacity-80 transition hover:bg-black/[0.08] hover:text-accent hover:opacity-100"
              aria-label="Удалить чат"
              @click="deleteChat(c.id, $event)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path
                  d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path d="M10 11v6M14 11v6" stroke-linecap="round" />
              </svg>
            </button>
          </div>
        </li>
        <li v-if="filteredChats.length === 0" class="px-[12px] py-[10px] text-[13px] text-ink-muted">
          Ничего не найдено
        </li>
      </ul>

      <div class="mt-auto shrink-0 pb-0">
        <button
          type="button"
          class="flex w-full items-center gap-3 px-[16px] py-[16px] text-left text-[13px] font-semibold text-black"
          @click="openSettings"
        >
          <svg
            class="shrink-0 text-black"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"
            />
            <circle cx="12" cy="12" r="3" />
          </svg>
          Настройки и справка
        </button>
      </div>
    </template>
  </aside>
</template>
