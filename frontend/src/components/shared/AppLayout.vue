<template>
  <div class="hms-layout">

    <!-- ── Mobile top bar ─────────────────────── -->
    <div class="hms-topbar">
      <button class="hms-hamburger" @click="sidebarOpen = !sidebarOpen"
              :aria-label="sidebarOpen ? 'Close menu' : 'Open menu'">
        {{ sidebarOpen ? '✕' : '☰' }}
      </button>
      <span style="font-weight:700;font-size:15px;">🏥 HMS</span>
      <span style="font-size:12px;color:#adb5bd;">{{ roleLabel }}</span>
    </div>

    <!-- ── Sidebar overlay (mobile) ───────────── -->
    <div class="hms-overlay" :class="{ open: sidebarOpen }"
         @click="sidebarOpen = false"></div>

    <!-- ── Sidebar ──────────────────────────────── -->
    <nav class="hms-sidebar" :class="{ open: sidebarOpen }"
         role="navigation" :aria-label="`${roleLabel} navigation`">

      <!-- Brand -->
      <div class="brand">
        <div class="brand-name">🏥 HMS V2</div>
        <div class="brand-role">{{ displayName }}</div>
        <div style="font-size:10px;color:#6c757d;margin-top:2px;">{{ roleLabel }}</div>
      </div>

      <!-- Nav items -->
      <div class="nav-section">
        <button
          v-for="item in navItems"
          :key="item.view"
          class="hms-nav-item"
          :class="{ active: activeView === item.view }"
          @click="handleNav(item.view)"
          :aria-current="activeView === item.view ? 'page' : undefined"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
          <span v-if="item.badge"
                class="badge bg-danger rounded-pill ms-auto"
                style="font-size:10px;">{{ item.badge }}</span>
        </button>
      </div>

      <!-- Footer -->
      <div class="sidebar-footer">
        <button class="btn btn-outline-danger btn-sm w-100"
                @click="$emit('logout')">
          Sign Out
        </button>
      </div>
    </nav>

    <!-- ── Main content ────────────────────────── -->
    <main class="hms-main" role="main">
      <div class="hms-content">

        <!-- Page header -->
        <div class="hms-page-header">
          <h1 class="hms-page-title">{{ currentTitle }}</h1>
          <slot name="header-right">
            <span class="badge bg-light text-dark border small px-3 py-2">
              {{ today }}
            </span>
          </slot>
        </div>

        <!-- Routed content -->
        <slot />
      </div>
    </main>

    <!-- ── Toast container ─────────────────────── -->
    <ToastContainer />

    <!-- ── PWA install banner ──────────────────── -->
    <PWAInstallBanner />
  </div>
</template>

<script>
import ToastContainer  from './ToastContainer.vue'
import PWAInstallBanner from './PWAInstallBanner.vue'

export default {
  name: 'AppLayout',
  components: { ToastContainer, PWAInstallBanner },
  props: {
    navItems:    { type: Array,  required: true },
    activeView:  { type: String, required: true },
    displayName: { type: String, default: '' },
    roleLabel:   { type: String, default: '' },
    titleMap:    { type: Object, default: () => ({}) },
  },
  emits: ['update:activeView', 'logout'],
  data() {
    return { sidebarOpen: false }
  },
  computed: {
    currentTitle() { return this.titleMap[this.activeView] || '' },
    today() {
      return new Date().toLocaleDateString('en-IN', {
        weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
      })
    },
  },
  methods: {
    handleNav(view) {
      this.$emit('update:activeView', view)
      this.sidebarOpen = false   // auto-close on mobile
    },
  },
}
</script>
