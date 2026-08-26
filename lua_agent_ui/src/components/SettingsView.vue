<script setup lang="ts">
import { reactive, ref } from 'vue'

type SettingsPayload = {
  num_ctx?: number
  num_predict?: number
  num_batch?: number
  num_parallel?: number
  temperature?: number
  top_p?: number
  repeat_penalty?: number
}

type SettingsWsEvent =
  | { event: 'settings_updated'; settings: Record<string, number> }
  | { event: 'settings_reset'; settings: Record<string, number> }
  | { event: 'error'; detail: string }

const WS_SETTINGS_URL = import.meta.env.VITE_WS_SETTINGS_URL ?? 'ws://localhost:8080/ws/update_settings'

const form = reactive<Required<SettingsPayload>>({
  num_ctx: 4096,
  num_predict: 256,
  num_batch: 1,
  num_parallel: 1,
  temperature: 0.15,
  top_p: 0.9,
  repeat_penalty: 1.1,
})

const isSaving = ref(false)
const feedback = ref<string | null>(null)
const feedbackError = ref(false)

function applySettingsFromServer(settings: Record<string, number>) {
  form.num_ctx = Number(settings.num_ctx ?? form.num_ctx)
  form.num_predict = Number(settings.num_predict ?? form.num_predict)
  form.num_batch = Number(settings.num_batch ?? form.num_batch)
  form.num_parallel = Number(settings.num_parallel ?? form.num_parallel)
  form.temperature = Number(settings.temperature ?? form.temperature)
  form.top_p = Number(settings.top_p ?? form.top_p)
  form.repeat_penalty = Number(settings.repeat_penalty ?? form.repeat_penalty)
}

function sendViaSocket(payload: { settings: SettingsPayload | null | Record<string, never> }) {
  return new Promise<SettingsWsEvent>((resolve, reject) => {
    const ws = new WebSocket(WS_SETTINGS_URL)

    ws.onopen = () => {
      ws.send(JSON.stringify(payload))
    }

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as SettingsWsEvent
        resolve(parsed)
      } catch {
        reject(new Error('Некорректный ответ сервера настроек'))
      } finally {
        ws.close()
      }
    }

    ws.onerror = () => {
      reject(new Error('Не удалось подключиться к серверу настроек'))
      ws.close()
    }
  })
}

async function saveSettings() {
  isSaving.value = true
  feedback.value = null
  feedbackError.value = false

  try {
    const event = await sendViaSocket({
      settings: {
        num_ctx: Number(form.num_ctx),
        num_predict: Number(form.num_predict),
        num_batch: Number(form.num_batch),
        num_parallel: Number(form.num_parallel),
        temperature: Number(form.temperature),
        top_p: Number(form.top_p),
        repeat_penalty: Number(form.repeat_penalty),
      },
    })

    if (event.event === 'error') {
      feedback.value = event.detail
      feedbackError.value = true
      return
    }

    applySettingsFromServer(event.settings)
    feedback.value = event.event === 'settings_reset' ? 'Настройки сброшены к дефолтным' : 'Настройки применены'
  } catch (err) {
    feedback.value = err instanceof Error ? err.message : 'Ошибка применения настроек'
    feedbackError.value = true
  } finally {
    isSaving.value = false
  }
}

async function resetSettings() {
  isSaving.value = true
  feedback.value = null
  feedbackError.value = false

  try {
    const event = await sendViaSocket({ settings: {} })
    if (event.event === 'error') {
      feedback.value = event.detail
      feedbackError.value = true
      return
    }
    applySettingsFromServer(event.settings)
    feedback.value = 'Настройки сброшены к дефолтным'
  } catch (err) {
    feedback.value = err instanceof Error ? err.message : 'Ошибка сброса настроек'
    feedbackError.value = true
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 bg-page px-6 py-6 md:px-10">
    <section class="mx-auto w-full max-w-composer rounded-[20px] border border-border bg-surface p-5 md:p-6">
      <h2 class="text-[24px] font-bold text-black [font-family:var(--font-display)]">Настройки и справка</h2>

      <div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
        <label class="text-[13px] text-ink-secondary">
          num_ctx
          <input v-model.number="form.num_ctx" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
        <label class="text-[13px] text-ink-secondary">
          num_predict
          <input v-model.number="form.num_predict" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
        <label class="text-[13px] text-ink-secondary">
          num_batch
          <input v-model.number="form.num_batch" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
        <label class="text-[13px] text-ink-secondary">
          num_parallel
          <input v-model.number="form.num_parallel" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
        <label class="text-[13px] text-ink-secondary">
          temperature
          <input v-model.number="form.temperature" step="0.01" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
        <label class="text-[13px] text-ink-secondary">
          top_p
          <input v-model.number="form.top_p" step="0.01" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
        <label class="text-[13px] text-ink-secondary md:col-span-2">
          repeat_penalty
          <input v-model.number="form.repeat_penalty" step="0.01" type="number" class="mt-1 w-full rounded-lg border border-border bg-page px-3 py-2 text-ink" />
        </label>
      </div>

      <div class="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          :disabled="isSaving"
          class="rounded-lg bg-accent px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
          @click="saveSettings"
        >
          Применить
        </button>
        <button
          type="button"
          :disabled="isSaving"
          class="rounded-lg border border-border px-4 py-2 text-[13px] font-semibold text-ink disabled:opacity-50"
          @click="resetSettings"
        >
          Сбросить к дефолтам
        </button>
      </div>

      <p v-if="feedback" class="mt-3 text-[13px]" :class="feedbackError ? 'text-accent' : 'text-ink-secondary'">
        {{ feedback }}
      </p>
    </section>
  </div>
</template>
