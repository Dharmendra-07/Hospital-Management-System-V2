<template>
  <div class="min-vh-100 d-flex flex-column align-items-center justify-content-center text-center">
    <h1 class="display-1 text-danger">403</h1>
    <h4>Unauthorized Access</h4>
    <p class="text-muted">You don't have permission to view this page.</p>
    <router-link to="/login" class="btn btn-primary">Back to Login</router-link>
  </div>
</template>
<script>export default { name: 'Unauthorized' }</script>
