<template>
  <div class="min-vh-100 d-flex flex-column align-items-center justify-content-center text-center">
    <h1 class="display-1 text-secondary">404</h1>
    <h4>Page Not Found</h4>
    <p class="text-muted">The page you are looking for does not exist.</p>
    <router-link to="/" class="btn btn-primary">Go Home</router-link>
  </div>
</template>
<script>export default { name: 'NotFound' }</script>
