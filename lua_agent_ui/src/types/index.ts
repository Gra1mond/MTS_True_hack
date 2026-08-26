export interface MessageContent {
  type: 'text' | 'code' | 'diff'
  text?: string
  language?: string
  code?: string
  diffOld?: string
  diffNew?: string
  totalLines?: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: MessageContent[]
  timestamp: Date
}

export interface Chat {
  id: string
  title: string
  messages: Message[]
}

export type AgentName = 'planner' | 'coder' | 'validator' | 'clarifier'

export type AgentStatus = 'idle' | 'active' | 'done' | 'error'

export interface Project {
  name: string
  path?: string
  created_at?: string
}

export interface GenerateRequest {
  event?: 'generate'
  prompt: string
  request_id?: string
}

export interface GenerateResponse {
  code: string
}

export interface GenerationCompleteEvent {
  event: 'generation_complete'
  prompt: string
  raw_lua: string
  lowcode: Record<string, string>
  retries: number
  timestamp: string
  request_id?: string
}

export interface ClarificationRequestEvent {
  event: 'clarification_request'
  question: string
  iteration: number
  request_id?: string
}

export interface GenerationStartedEvent {
  event: 'generation_started'
  request_id?: string
}

export interface ErrorEvent {
  event: 'error'
  detail: string
}

export type BackendWsMessage =
  | GenerationCompleteEvent
  | ClarificationRequestEvent
  | GenerationStartedEvent
  | ErrorEvent
