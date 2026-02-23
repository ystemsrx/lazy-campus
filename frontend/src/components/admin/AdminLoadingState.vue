<template>
  <div class="sk-main">
    <div class="sk-stats-grid">
      <div v-for="i in 6" :key="i" class="sk-stat-card">
        <div class="skeleton sk-stat-label"></div>
        <div class="skeleton sk-stat-value"></div>
        <div class="skeleton sk-stat-meta"></div>
      </div>
    </div>

    <div class="sk-chart-grid">
      <div class="sk-chart-card">
        <div class="skeleton sk-chart-title"></div>
        <div class="skeleton sk-chart-area"></div>
      </div>
      <div class="sk-chart-card">
        <div class="skeleton sk-chart-title"></div>
        <div class="sk-list-items">
          <div v-for="j in 4" :key="j" class="skeleton sk-list-item"></div>
        </div>
      </div>
    </div>

    <div class="sk-reg-card">
      <div class="sk-reg-left">
        <div class="skeleton sk-reg-title"></div>
        <div class="skeleton sk-reg-desc"></div>
      </div>
      <div class="skeleton sk-reg-btn"></div>
    </div>
  </div>
</template>

<style scoped>
.sk-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sk-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.sk-stats-grid > :nth-child(1) .skeleton { animation-delay: 0s; }
.sk-stats-grid > :nth-child(2) .skeleton { animation-delay: 0.07s; }
.sk-stats-grid > :nth-child(3) .skeleton { animation-delay: 0.14s; }
.sk-stats-grid > :nth-child(4) .skeleton { animation-delay: 0.21s; }
.sk-stats-grid > :nth-child(5) .skeleton { animation-delay: 0.28s; }
.sk-stats-grid > :nth-child(6) .skeleton { animation-delay: 0.35s; }

.sk-stat-card {
  background: var(--c-surface);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  box-shadow: var(--shadow-card);
}

.sk-stat-label {
  height: 13px;
  width: 72px;
  border-radius: var(--radius-sm);
}

.sk-stat-value {
  height: 34px;
  width: 80px;
  border-radius: var(--radius-sm);
}

.sk-stat-meta {
  height: 12px;
  width: 140px;
  border-radius: var(--radius-sm);
}

.sk-chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 16px;
}

.sk-chart-card {
  background: var(--c-surface);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-card);
}

.sk-chart-title {
  height: 18px;
  width: 120px;
  border-radius: var(--radius-sm);
}

.sk-chart-area {
  height: 200px;
  border-radius: var(--radius-lg);
}

.sk-list-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sk-list-item {
  height: 40px;
  border-radius: var(--radius-md);
}

.sk-reg-card {
  background: var(--c-surface);
  border: 1.5px dashed rgba(203, 213, 225, 0.7);
  border-radius: var(--radius-2xl);
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  box-shadow: var(--shadow-card);
}

.sk-reg-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sk-reg-title {
  height: 18px;
  width: 90px;
  border-radius: var(--radius-sm);
}

.sk-reg-desc {
  height: 13px;
  width: 200px;
  border-radius: var(--radius-sm);
}

.sk-reg-btn {
  height: 40px;
  width: 110px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
}

@media (max-width: 1150px) {
  .sk-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sk-chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .sk-stats-grid {
    grid-template-columns: 1fr;
  }

  .sk-reg-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .sk-reg-btn {
    width: 100%;
  }
}
</style>
