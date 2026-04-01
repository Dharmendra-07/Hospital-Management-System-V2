<template>
  <transition name="slide-up">
    <div v-if="canInstall" class="pwa-install-banner" role="complementary"
         aria-label="Install HMS as an app">
      <span class="pwa-icon">🏥</span>
      <div class="pwa-text">
        <div class="pwa-title">Add HMS to your home screen</div>
        <div class="pwa-desc">
          Access the Hospital Management System instantly, even offline.
        </div>
      </div>
      <div class="d-flex gap-2 flex-shrink-0">
        <button class="btn btn-outline-secondary btn-sm" @click="dismiss">
          Not now
        </button>
        <button class="btn btn-primary btn-sm" @click="handleInstall">
          Install
        </button>
      </div>
    </div>
  </transition>
</template>

<script>
import { usePWA } from '../../composables/usePWA'
import { useToast } from '../../composables/useToast'

export default {
  name: 'PWAInstallBanner',
  setup() {
    const { canInstall, install, dismiss } = usePWA()
    const toast = useToast()

    async function handleInstall() {
      const accepted = await install()
      if (accepted) {
        toast.success('HMS installed!', 'Find it on your home screen.')
      }
    }

    return { canInstall, handleInstall, dismiss }
  },
}
</script>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active { transition: transform .35s ease, opacity .35s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); opacity: 0; }
</style>
