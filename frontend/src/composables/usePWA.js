/**
 * frontend/src/composables/usePWA.js
 * Manages the browser's beforeinstallprompt event for Add to Home Screen.
 *
 * Usage:
 *   const { canInstall, install, dismiss } = usePWA()
 */

import { ref } from 'vue'

const deferredPrompt = ref(null)
const canInstall     = ref(false)
const dismissed      = ref(
  localStorage.getItem('pwa-dismissed') === 'true'
)

// Listen once at module load so we don't miss early events
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  deferredPrompt.value = e
  if (!dismissed.value) {
    canInstall.value = true
  }
})

window.addEventListener('appinstalled', () => {
  canInstall.value    = false
  deferredPrompt.value = null
})

export function usePWA() {
  async function install() {
    if (!deferredPrompt.value) return false
    deferredPrompt.value.prompt()
    const { outcome } = await deferredPrompt.value.userChoice
    deferredPrompt.value = null
    canInstall.value     = false
    return outcome === 'accepted'
  }

  function dismiss() {
    canInstall.value = false
    dismissed.value  = true
    localStorage.setItem('pwa-dismissed', 'true')
  }

  return { canInstall, install, dismiss }
}
