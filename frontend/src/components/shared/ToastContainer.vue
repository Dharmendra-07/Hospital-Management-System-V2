<template>
  <div class="hms-toast-container" aria-live="polite" aria-atomic="true">
    <div
      v-for="t in toasts"
      :key="t.id"
      :class="['hms-toast', `toast-${t.type}`, { leaving: t.leaving }]"
      role="alert"
    >
      <span class="hms-toast-icon">{{ icons[t.type] }}</span>
      <div style="flex:1;min-width:0;">
        <div class="hms-toast-title">{{ t.title }}</div>
        <div v-if="t.body" class="hms-toast-body">{{ t.body }}</div>
      </div>
      <button class="hms-toast-close" @click="remove(t.id)" aria-label="Dismiss">✕</button>
    </div>
  </div>
</template>

<script>
import { useToast } from '../../composables/useToast'

export default {
  name: 'ToastContainer',
  setup() {
    const { toasts, remove, icons } = useToast()
    return { toasts, remove, icons }
  },
}
</script>
