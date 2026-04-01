/**
 * frontend/src/composables/useToast.js
 * Lightweight toast notification composable.
 *
 * Usage (in any Vue component):
 *   import { useToast } from '@/composables/useToast'
 *   const toast = useToast()
 *   toast.success('Appointment booked!')
 *   toast.error('Something went wrong.')
 *   toast.info('Processing your request…')
 *   toast.warning('Cache may be stale.')
 */

import { reactive } from 'vue'

// Shared reactive state — one instance across the entire app
const state = reactive({ toasts: [] })
let _id = 0

function add(type, title, body = '', duration = 3500) {
  const id = ++_id
  state.toasts.push({ id, type, title, body, leaving: false })

  // Auto-dismiss
  setTimeout(() => remove(id), duration)
  return id
}

function remove(id) {
  const idx = state.toasts.findIndex(t => t.id === id)
  if (idx === -1) return
  state.toasts[idx].leaving = true
  setTimeout(() => {
    const i = state.toasts.findIndex(t => t.id === id)
    if (i !== -1) state.toasts.splice(i, 1)
  }, 320)
}

const icons = {
  success: '✅',
  danger:  '❌',
  info:    'ℹ️',
  warning: '⚠️',
}

export function useToast() {
  return {
    success: (title, body) => add('success', title, body),
    error:   (title, body) => add('danger',  title, body),
    info:    (title, body) => add('info',    title, body),
    warning: (title, body) => add('warning', title, body),
    remove,
    toasts:  state.toasts,
    icons,
  }
}

export { state as toastState }
