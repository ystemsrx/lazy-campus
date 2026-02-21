<template>
  <div class="tm-page-title">
    <h1>任务<span>管理</span></h1>
    <p>管理你发布和接取的所有任务</p>
  </div>
</template>

<style scoped>
.tm-page-title {
  padding: 28px 32px 0;
  flex-shrink: 0;
}

.tm-page-title h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: var(--c-text);
  display: flex;
  align-items: center;
  gap: 4px;
  line-height: 1.2;
}

.tm-page-title h1 span {
  color: var(--c-accent);
}

.tm-page-title p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--c-text-muted);
  font-weight: 500;
}

@media (max-width: 900px) {
  .tm-page-title {
    padding: 20px 16px 0;
  }

  .tm-page-title h1 {
    font-size: 22px;
  }
}
</style>
