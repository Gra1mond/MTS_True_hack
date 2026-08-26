<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import SettingsView from './components/SettingsView.vue'
import AppTopBar from './components/AppTopBar.vue'
import ChatView from './components/ChatView.vue'
import WelcomeScreen from './components/WelcomeScreen.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useChatStore } from './stores/chat'

const store = useChatStore()
const route = useRoute()
const { activeChatId, activeChat, isProcessing, activeAgent, processingStartedAt } = storeToRefs(store)
const { connect, disconnect } = useWebSocket()

const sidebarCollapsed = ref(false)

function onSend(text: string) {
  store.sendMessage(text)
}

onMounted(() => {
  void connect()
  void store.loadProjects()
})

onBeforeUnmount(() => {
  disconnect()
})
</script>

<template>
  <div class="flex h-dvh max-h-dvh flex-col bg-page">
    <div class="flex min-h-0 flex-1">
      <AppSidebar
        v-if="route.name !== 'settings'"
        :collapsed="sidebarCollapsed"
        @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"
      />
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <AppTopBar />
        <SettingsView v-if="route.name === 'settings'" />
        <template v-else>
          <WelcomeScreen
            v-if="!activeChatId"
            :disabled="isProcessing"
            @send="onSend"
          />
          <ChatView
            v-else-if="activeChat"
            :messages="activeChat.messages"
            :disabled="isProcessing"
            :is-processing="isProcessing"
            :active-agent="activeAgent"
            :processing-started-at="processingStartedAt"
            @send="onSend"
          />
        </template>
      </div>
    </div>
  </div>
</template>
