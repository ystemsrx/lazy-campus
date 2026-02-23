<script setup lang="ts">
import AppConfirm from './components/AppConfirm.vue'
import AppSlideCaptcha from './components/AppSlideCaptcha.vue'
</script>

<template>
  <router-view />
  <AppConfirm />
  <AppSlideCaptcha />
</template>
