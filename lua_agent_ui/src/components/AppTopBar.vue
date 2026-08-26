<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'

type Theme = 'light' | 'dark'
const STORAGE_KEY = 'lua-agent-theme'
const theme = ref<Theme>('light')
let transitionResetTimer: number | null = null

const isDark = computed(() => theme.value === 'dark')
const buttonLabel = computed(() => (isDark.value ? 'Светлая тема' : 'Тёмная тема'))
const router = useRouter()
const route = useRoute()
const store = useChatStore()
const isSettingsRoute = computed(() => route.name === 'settings')

function markThemeTransition() {
  if (typeof document === 'undefined') {
    return
  }
  const root = document.documentElement
  root.classList.add('theme-switching')
  if (transitionResetTimer !== null) {
    window.clearTimeout(transitionResetTimer)
  }
  transitionResetTimer = window.setTimeout(() => {
    root.classList.remove('theme-switching')
    transitionResetTimer = null
  }, 500)
}

function applyTheme(nextTheme: Theme) {
  markThemeTransition()
  theme.value = nextTheme
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', nextTheme)
  }
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, nextTheme)
  }
}

function toggleTheme() {
  applyTheme(isDark.value ? 'light' : 'dark')
}

function onTitleClick() {
  store.newEmptyChat()
  void router.push('/')
}

function closeSettings() {
  void router.push('/')
}

onMounted(() => {
  const saved = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null
  if (saved === 'dark' || saved === 'light') {
    applyTheme(saved)
    return
  }
  applyTheme('light')
})

onBeforeUnmount(() => {
  if (transitionResetTimer !== null) {
    window.clearTimeout(transitionResetTimer)
  }
})
</script>

<template>
  <header class="flex shrink-0 items-start justify-between bg-surface pb-3 pl-[40px] pr-6 pt-[24px]">
    <button
      type="button"
      class="truncate text-[32px] font-bold leading-none tracking-[-0.02em] text-black [font-family:var(--font-extended)]"
      aria-label="Создать новый чат"
      @click="onTitleClick"
    >
      MTC LocalScript
    </button>
    <div class="flex shrink-0 items-center gap-3 text-ink-secondary">
      <button
        v-if="isSettingsRoute"
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-ink transition hover:bg-black/[0.06]"
        aria-label="Закрыть настройки"
        title="Закрыть настройки"
        @click="closeSettings"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
      <button
        v-else
        type="button"
        class="theme-toggle"
        :aria-label="buttonLabel"
        :title="buttonLabel"
        @click="toggleTheme"
      >
        <span class="theme-toggle__track">
          <svg
            class="theme-toggle__icon theme-toggle__icon--sun"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.8" />
            <path
              d="M12 2.5V5.2M12 18.8V21.5M21.5 12H18.8M5.2 12H2.5M18.7 5.3L16.8 7.2M7.2 16.8L5.3 18.7M18.7 18.7L16.8 16.8M7.2 7.2L5.3 5.3"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            />
          </svg>
          <svg
            class="theme-toggle__icon theme-toggle__icon--moon"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M20 14.5A8.5 8.5 0 1 1 10.5 5a7 7 0 1 0 9.5 9.5Z"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>

        </span>
        <span class="theme-toggle__thumb" :class="{ 'theme-toggle__thumb--dark': isDark }" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.theme-toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  width: 60px;
  height: 34px;
  padding: 4px;
  border-radius: 9999px;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-bg-white) 82%, var(--color-bg-sidebar));
  color: var(--color-text-secondary);
  transition: transform 0.2s ease, box-shadow 0.3s ease, border-color 0.3s ease, background-color 0.3s ease;
}

.theme-toggle:hover {
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.12);
}

.theme-toggle:active {
  transform: scale(0.97);
}

.theme-toggle__track {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  justify-content: space-between;
  padding: 0 3px;
}

.theme-toggle__icon {
  width: 15px;
  height: 15px;
  transition: transform 0.35s ease, opacity 0.35s ease, color 0.35s ease;
}

.theme-toggle__icon--sun {
  color: #f8a900;
  transform: scale(0.9) rotate(-10deg);
  opacity: 0.55;
}

.theme-toggle__icon--moon {
  color: #8ca5ff;
  transform: scale(1) rotate(0deg);
  opacity: 1;
}

.theme-toggle__thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #ffffff 0 35%, #eef1ff 70%, #d8dcf3 100%);
  box-shadow: 0 5px 12px rgba(13, 18, 40, 0.28);
  transition: transform 0.38s cubic-bezier(0.22, 1, 0.36, 1), background 0.32s ease;
}

.theme-toggle__thumb--dark {
  transform: translateX(26px);
  background: radial-gradient(circle at 35% 35%, #fefeff 0 28%, #e3e5f7 62%, #c7cbec 100%);
}

.theme-toggle:has(.theme-toggle__thumb--dark) .theme-toggle__icon--sun {
  transform: scale(1) rotate(0deg);
  opacity: 1;
}

.theme-toggle:has(.theme-toggle__thumb--dark) .theme-toggle__icon--moon {
  transform: scale(0.9) rotate(10deg);
  opacity: 0.55;
}
</style>
