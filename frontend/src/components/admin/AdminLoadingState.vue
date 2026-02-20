<template>
  <div class="sk-main">
    <!-- 标题 -->
    <div class="skeleton sk-page-title"></div>

    <!-- 统计卡片网格：6张，对应 Dashboard av-stats-grid -->
    <div class="sk-stats-grid">
      <div v-for="i in 6" :key="i" class="sk-stat-card">
        <div class="skeleton sk-stat-value"></div>
        <div class="skeleton sk-stat-label"></div>
      </div>
    </div>

    <!-- 注册控制卡片骨架 -->
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
/* ---- container: mirrors av-main ---- */
.sk-main {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

/* ---- page title ---- */
.sk-page-title {
  height: 28px;
  width: 120px;
  border-radius: var(--radius-sm);
  margin-bottom: 20px;
}

/* ---- stats grid: matches av-stats-grid ---- */
.sk-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

/* staggered shimmer */
.sk-stats-grid > :nth-child(1) .skeleton { animation-delay: 0s; }
.sk-stats-grid > :nth-child(2) .skeleton { animation-delay: 0.07s; }
.sk-stats-grid > :nth-child(3) .skeleton { animation-delay: 0.14s; }
.sk-stats-grid > :nth-child(4) .skeleton { animation-delay: 0.21s; }
.sk-stats-grid > :nth-child(5) .skeleton { animation-delay: 0.28s; }
.sk-stats-grid > :nth-child(6) .skeleton { animation-delay: 0.35s; }

.sk-stat-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.sk-stat-value {
  height: 36px;
  width: 64px;
  border-radius: var(--radius-sm);
}

.sk-stat-label {
  height: 13px;
  width: 56px;
  border-radius: var(--radius-sm);
}

/* ---- registration card: matches av-reg-card ---- */
.sk-reg-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.sk-reg-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sk-reg-title {
  height: 18px;
  width: 80px;
  border-radius: var(--radius-sm);
}

.sk-reg-desc {
  height: 13px;
  width: 180px;
  border-radius: var(--radius-sm);
}

.sk-reg-btn {
  height: 38px;
  width: 100px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
}

/* ---- responsive ---- */
@media (max-width: 768px) {
  .sk-main {
    padding: 16px;
  }

  .sk-stats-grid {
    grid-template-columns: repeat(2, 1fr);
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
