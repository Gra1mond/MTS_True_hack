import { ref } from 'vue'
import { useChatStore } from '../stores/chat'
import type { BackendWsMessage, GenerateRequest } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080/ws/generate'
const RETRY_DELAYS_MS = [1000, 2000, 4000, 8000, 16000] as const

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

const socket = ref<WebSocket | null>(null)
const isConnected = ref(false)
const status = ref<ConnectionStatus>('idle')

let reconnectAttempts = 0
let reconnectTimer: number | null = null
let shouldReconnect = true

function clearReconnectTimer() {
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

function resetReconnectState() {
  reconnectAttempts = 0
  clearReconnectTimer()
}

function scheduleReconnect() {
  const store = useChatStore()
  if (!shouldReconnect || reconnectAttempts >= RETRY_DELAYS_MS.length) {
    status.value = 'error'
    store.setConnected(false)
    store.setError('Не удалось переподключиться к серверу.')
    return
  }

  const delay = RETRY_DELAYS_MS[reconnectAttempts] ?? RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - 1]
  reconnectAttempts += 1
  clearReconnectTimer()
  reconnectTimer = window.setTimeout(() => {
    void connect()
  }, delay)
}

function handleMessage(message: BackendWsMessage) {
  const store = useChatStore()

  if (message.event === 'clarification_request') {
    store.handleClarificationRequest(message.question, message.request_id ?? null)
    return
  }

  if (message.event === 'generation_started') {
    store.handleGenerationStarted()
    return
  }

  if (message.event === 'generation_complete') {
    store.setAgentStatus('planner', 'done')
    store.setAgentStatus('coder', 'done')
    store.setAgentStatus('validator', 'done')
    store.setCodeReady(message.raw_lua, null, message)
    return
  }

  if (message.event === 'error') {
    store.setAgentStatus('validator', 'error')
    store.setError(message.detail)
  }
}

async function connect() {
  if (socket.value && (socket.value.readyState === WebSocket.OPEN || socket.value.readyState === WebSocket.CONNECTING)) {
    return
  }

  status.value = 'connecting'

  const ws = new WebSocket(WS_URL)
  socket.value = ws

  ws.onopen = () => {
    const store = useChatStore()
    resetReconnectState()
    status.value = 'connected'
    isConnected.value = true
    store.setConnected(true)
  }

  ws.onmessage = (event) => {
    try {
      handleMessage(JSON.parse(event.data) as BackendWsMessage)
    } catch {
      const store = useChatStore()
      store.setError('Сервер вернул некорректный JSON.')
    }
  }

  ws.onerror = () => {
    status.value = 'error'
  }

  ws.onclose = () => {
    const store = useChatStore()
    isConnected.value = false
    store.setConnected(false)
    socket.value = null

    if (shouldReconnect) {
      status.value = 'disconnected'
      scheduleReconnect()
      return
    }

    status.value = 'idle'
  }
}

function disconnect() {
  shouldReconnect = false
  clearReconnectTimer()
  if (socket.value) {
    socket.value.close()
    socket.value = null
  }
  isConnected.value = false
  status.value = 'idle'
  useChatStore().setConnected(false)
}

function send(payload: GenerateRequest) {
  const ws = socket.value
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return false
  }

  ws.send(JSON.stringify(payload))
  return true
}

function sendClarificationResponse(answer: string, requestId?: string | null) {
  const ws = socket.value
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return false
  }

  const payload: { event: 'clarification_response'; answer: string; request_id?: string } = {
    event: 'clarification_response',
    answer,
  }
  if (requestId) payload.request_id = requestId
  ws.send(JSON.stringify(payload))
  return true
}

export function useWebSocket() {
  shouldReconnect = true

  return {
    connect,
    disconnect,
    send,
    sendClarificationResponse,
    isConnected,
    status,
  }
}
