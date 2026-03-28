<template>
  <span :class="badgeClass">{{ status }}</span>
</template>

<script>
export default {
  name: 'StatusBadge',
  props: {
    status: { type: String, required: true },
  },
  computed: {
    badgeClass() {
      return {
        Booked:    'badge bg-primary',
        Completed: 'badge bg-success',
        Cancelled: 'badge bg-danger',
      }[this.status] || 'badge bg-secondary'
    },
  },
}
</script>
