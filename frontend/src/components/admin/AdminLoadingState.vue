<template>
  <div class="av-loading">
    <div class="spinner"></div>
    <span>加载中…</span>
  </div>
</template>

<style scoped>
.av-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: calc(100vh - 60px);
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}
</style>
