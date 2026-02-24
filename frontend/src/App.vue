<script setup lang="ts">
import AppConfirm from './components/AppConfirm.vue'
import AppSlideCaptcha from './components/AppSlideCaptcha.vue'

const cachedViews = ['HomeView', 'TaskManagementView', 'SettingsView', 'ChatView', 'MyReportsView']
</script>

<template>
  <router-view v-slot="{ Component }">
    <keep-alive :include="cachedViews">
      <component :is="Component" />
    </keep-alive>
  </router-view>
  <AppConfirm />
  <AppSlideCaptcha />
</template>
