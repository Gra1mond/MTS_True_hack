import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { fetchProjects } from '../api/client'
import { useWebSocket } from '../composables/useWebSocket'
import type {
  AgentName,
  AgentStatus,
  BackendWsMessage,
  Chat,
  Message,
  Project,
} from '../types'

const CHAT_STORAGE_KEY = 'lua-agent-chat-state-v1'
const CHAT_DEFAULT_TITLE = 'Новый чат'

interface PersistedChatState {
  chats: Chat[]
  activeChatId: string | null
}

interface ClarificationState {
  requestId: string | null
  question: string
}

export const useChatStore = defineStore('chat', () => {
  const chats = ref<Chat[]>([])
  const activeChatId = ref<string | null>(null)
  const activeAgent = ref<AgentName | null>(null)
  const agentStatuses = ref<Record<AgentName, AgentStatus>>({
    planner: 'idle',
    coder: 'idle',
    validator: 'idle',
    clarifier: 'idle',
  })
  const isConnected = ref(false)
  const isProcessing = ref(false)
  const processingStartedAt = ref<Date | null>(null)
  const processingElapsedMs = ref(0)
  const currentProjectPath = ref<string | null>(null)
  const projects = ref<Project[]>([])
  const error = ref<string | null>(null)
  const pendingClarification = ref<ClarificationState | null>(null)

  function normalizeChats(rawChats: unknown): Chat[] {
    if (!Array.isArray(rawChats)) return []
    return rawChats
      .filter((chat): chat is Chat => !!chat && typeof chat === 'object')
      .map((chat) => {
        const messages = Array.isArray(chat.messages) ? chat.messages : []
        return {
          ...chat,
          messages: messages
            .filter((message): message is Message => !!message && typeof message === 'object')
            .map((message) => ({
              ...message,
              timestamp: new Date(message.timestamp),
            })),
        }
      })
      .filter((chat) => typeof chat.id === 'string' && typeof chat.title === 'string')
  }

  function loadPersistedState() {
    if (typeof window === 'undefined') return

    try {
      const raw = window.localStorage.getItem(CHAT_STORAGE_KEY)
      if (!raw) return

      const parsed = JSON.parse(raw) as Partial<PersistedChatState>
      chats.value = normalizeChats(parsed.chats)
      activeChatId.value = typeof parsed.activeChatId === 'string' ? parsed.activeChatId : null

      if (activeChatId.value && !chats.value.some((chat) => chat.id === activeChatId.value)) {
        activeChatId.value = chats.value[0]?.id ?? null
      }
    } catch (err) {
      console.error('Failed to load chat state from localStorage', err)
    }
  }

  function savePersistedState() {
    if (typeof window === 'undefined') return

    const payload: PersistedChatState = {
      chats: chats.value,
      activeChatId: activeChatId.value,
    }

    try {
      window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(payload))
    } catch (err) {
      console.error('Failed to save chat state to localStorage', err)
    }
  }

  loadPersistedState()

  watch([chats, activeChatId], savePersistedState, { deep: true })

  const activeChat = computed(() => chats.value.find((c) => c.id === activeChatId.value) ?? null)

  function setActiveChat(id: string | null) {
    activeChatId.value = id
  }

  function resetAgentStatuses() {
    agentStatuses.value = {
      planner: 'idle',
      coder: 'idle',
      validator: 'idle',
      clarifier: 'idle',
    }
    activeAgent.value = null
  }

  function createChat(firstMessage: string): Chat {
    const chat: Chat = {
      id: crypto.randomUUID(),
      title: buildChatTitle(firstMessage),
      messages: [
        {
          id: crypto.randomUUID(),
          role: 'user',
          content: [{ type: 'text', text: firstMessage }],
          timestamp: new Date(),
        },
      ],
    }
    chats.value.unshift(chat)
    activeChatId.value = chat.id
    return chat
  }

  function sendMessage(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return

    if (pendingClarification.value) {
      sendClarificationAnswer(trimmed)
      return
    }


    const createdNewChat = !activeChatId.value
    const chat = createdNewChat ? createChat(trimmed) : chats.value.find((c) => c.id === activeChatId.value)
    if (!chat) return

    if (!createdNewChat) {
      chat.messages.push({
        id: crypto.randomUUID(),
        role: 'user',
        content: [{ type: 'text', text: trimmed }],
        timestamp: new Date(),
      })

      if (chat.title === CHAT_DEFAULT_TITLE) {
        chat.title = buildChatTitle(trimmed)
      }
    }

    error.value = null
    processingElapsedMs.value = 0
    isProcessing.value = true
    processingStartedAt.value = new Date()
    setAgentStatus('planner', 'active')
    setAgentStatus('coder', 'idle')
    setAgentStatus('validator', 'idle')
    setAgentStatus('clarifier', 'idle')

    const { send } = useWebSocket()
    const sent = send({ event: 'generate', prompt: trimmed, request_id: chat.id })

    if (!sent) {
      processingStartedAt.value = null
      processingElapsedMs.value = 0
      setError('Нет соединения с сервером.')
    }
  }

  function sendCommand(cmd: '/new' | '/help' | '/exit') {
    if (cmd === '/new') {
      newEmptyChat()
      resetAgentStatuses()
      isProcessing.value = false
      processingStartedAt.value = null
      error.value = null
      return
    }

    const helpText =
      cmd === '/help'
        ? 'Доступны команды CLI: /new, /help, /exit. Через веб-интерфейс отправляется только генерация Lua-кода.'
        : 'Команда /exit недоступна через веб-интерфейс.'

    addAssistantMessage([
      { type: 'text', text: helpText },
    ])
  }

  function newEmptyChat() {
    const chat: Chat = {
      id: crypto.randomUUID(),
      title: CHAT_DEFAULT_TITLE,
      messages: [],
    }
    chats.value.unshift(chat)
    activeChatId.value = chat.id
    pendingClarification.value = null
  }

  function deleteChat(id: string) {
    const idx = chats.value.findIndex((c) => c.id === id)
    if (idx === -1) return
    chats.value.splice(idx, 1)
    if (activeChatId.value === id) {
      activeChatId.value = chats.value[0]?.id ?? null
    }
  }

  function addAssistantMessage(content: Message['content']) {
    const chat = chats.value.find((c) => c.id === activeChatId.value)
    if (!chat) return

    chat.messages.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content,
      timestamp: new Date(),
    })
  }

  function addAgentMessage(agent: AgentName, text: string) {
    setAgentStatus(agent, 'active')
    addAssistantMessage([{ type: 'text', text: agentLabel(agent) }, { type: 'text', text }])
  }

  function setAgentStatus(agent: AgentName, status: AgentStatus) {
    agentStatuses.value = {
      ...agentStatuses.value,
      [agent]: status,
    }
    activeAgent.value = status === 'active' ? agent : activeAgent.value === agent ? null : activeAgent.value
  }

  function setCodeReady(code: string, path: string | null, payload?: BackendWsMessage) {
    currentProjectPath.value = path
    isProcessing.value = false
    pendingClarification.value = null
    const startedAt = processingStartedAt.value
    processingStartedAt.value = null
    processingElapsedMs.value = 0

    const content: Message['content'] = [
      { type: 'text', text: 'Генерация завершена' },
    ]

    if (payload && payload.event === 'generation_complete') {
      const elapsedMs = startedAt ? Math.max(0, Date.now() - startedAt.getTime()) : null
      content.push({
        type: 'text',
        text: `Повторов исправления: ${payload.retries}. Затраченное время: ${formatDuration(elapsedMs)}.`,
      })
    }

    content.push({ type: 'code', language: 'lua', code })

    if (payload && payload.event === 'generation_complete') {
      const hasLowcode = payload.lowcode && Object.keys(payload.lowcode).length > 0
      if (hasLowcode) {
        content.push({ type: 'text', text: 'Lowcode' })
        content.push({
          type: 'code',
          language: 'json',
          code: JSON.stringify(payload.lowcode, null, 2),
        })
      }
    }

    addAssistantMessage(content)
  }


  function setValidationResult(_status: 'OK' | 'FIX', _issues: string[]) {
    // Реальный бэкенд не присылает отдельный validation_result.
  }

  function addClarificationQuestions(questions: string[]) {
    if (!questions.length) return
    addAssistantMessage([
      { type: 'text', text: 'Нужно уточнение' },
      ...questions.map((question) => ({ type: 'text' as const, text: question })),
    ])
  }

  function setConnected(value: boolean) {
    isConnected.value = value
  }

  function setError(message: string) {
    error.value = message
    isProcessing.value = false
    processingStartedAt.value = null
    processingElapsedMs.value = 0
    pendingClarification.value = null
    setAgentStatus('validator', 'error')
    addAssistantMessage([{ type: 'text', text: 'Ошибка' }, { type: 'text', text: message }])
  }

  function handleClarificationRequest(question: string, requestId: string | null) {
    if (isProcessing.value && processingStartedAt.value) {
      processingElapsedMs.value += Math.max(0, Date.now() - processingStartedAt.value.getTime())
    }
    pendingClarification.value = { question, requestId }
    isProcessing.value = false
    processingStartedAt.value = null
    setAgentStatus('planner', 'idle')
    setAgentStatus('coder', 'idle')
    setAgentStatus('validator', 'idle')
    setAgentStatus('clarifier', 'active')
    addAssistantMessage([
      { type: 'text', text: 'Нужно уточнение' },
      { type: 'text', text: question },
    ])
  }

  function handleGenerationStarted() {
    isProcessing.value = true
    processingStartedAt.value = new Date(Date.now() - processingElapsedMs.value)
    pendingClarification.value = null
    setAgentStatus('clarifier', 'done')
    setAgentStatus('planner', 'active')
    setAgentStatus('coder', 'idle')
    setAgentStatus('validator', 'idle')
  }

  function sendClarificationAnswer(answer: string) {
    const active = pendingClarification.value
    if (!active) return
    const chat = chats.value.find((c) => c.id === activeChatId.value)
    if (!chat) return

    chat.messages.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: [{ type: 'text', text: answer }],
      timestamp: new Date(),
    })

    const { sendClarificationResponse } = useWebSocket()
    const sent = sendClarificationResponse(answer, active.requestId ?? chat.id)
    if (!sent) {
      setError('Нет соединения с сервером.')
      return
    }

    isProcessing.value = true
    setAgentStatus('clarifier', 'done')
    pendingClarification.value = null
  }

  function formatDuration(ms: number | null): string {
    if (ms == null || Number.isNaN(ms)) return 'недоступно'
    const totalSeconds = Math.round(ms / 1000)
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes}м ${seconds.toString().padStart(2, '0')}с`
  }

  function buildChatTitle(prompt: string): string {
    const normalized = prompt
      .replace(/\s+/g, ' ')
      .replace(/^[\s.,!?;:()[\]{}"']+|[\s.,!?;:()[\]{}"']+$/g, '')
      .trim()
    if (!normalized) return CHAT_DEFAULT_TITLE

    const words = normalized.split(' ').slice(0, 5)
    const candidate = words.join(' ')
    const maxLength = 42
    return candidate.length > maxLength ? `${candidate.slice(0, maxLength)}…` : candidate
  }

  async function loadProjects() {
    const items = await fetchProjects()
    projects.value = items ?? []
  }

  function agentLabel(agent: AgentName) {
    if (agent === 'clarifier') return 'Clarifier'
    if (agent === 'planner') return 'Planner'
    if (agent === 'coder') return 'Coder'
    return 'Validator'
  }


  return {
    chats,
    activeChatId,
    activeChat,
    activeAgent,
    agentStatuses,
    isConnected,
    isProcessing,
    processingStartedAt,
    currentProjectPath,
    projects,
    error,
    pendingClarification,
    setActiveChat,
    createChat,
    sendMessage,
    sendCommand,
    newEmptyChat,
    deleteChat,
    addAgentMessage,
    setAgentStatus,
    setCodeReady,
    setValidationResult,
    addClarificationQuestions,
    setConnected,
    setError,
    handleClarificationRequest,
    handleGenerationStarted,
    loadProjects,
  }
})
