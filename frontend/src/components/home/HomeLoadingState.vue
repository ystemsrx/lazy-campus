<template>
  <div class="sk-main">
    <!-- 工具栏骨架 -->
    <div class="sk-toolbar">
      <div class="skeleton sk-search"></div>
      <div class="skeleton sk-sort-btn"></div>
    </div>

    <!-- 主布局 -->
    <div class="sk-layout">
      <!-- 桌面端侧边栏 -->
      <aside class="sk-sidebar">
        <div v-for="i in 5" :key="i" class="skeleton sk-sidebar-item"></div>
      </aside>

      <!-- 任务卡片网格 -->
      <div class="sk-grid">
        <div v-for="i in 6" :key="i" class="sk-card">
          <!-- top row: badges + deadline -->
          <div class="sk-card__top">
            <div class="sk-card__badges">
              <div class="skeleton sk-badge"></div>
              <div class="skeleton sk-badge sk-badge--narrow"></div>
            </div>
            <div class="skeleton sk-deadline"></div>
          </div>

          <!-- title -->
          <div class="skeleton sk-title"></div>

          <!-- description lines -->
          <div class="skeleton sk-desc"></div>
          <div class="skeleton sk-desc sk-desc--short"></div>

          <!-- tags -->
          <div class="sk-tags">
            <div class="skeleton sk-tag"></div>
            <div class="skeleton sk-tag sk-tag--wide"></div>
          </div>

          <!-- footer -->
          <div class="sk-footer">
            <div class="sk-pub">
              <div class="skeleton sk-pub-label"></div>
              <div class="skeleton sk-pub-name"></div>
            </div>
            <div class="skeleton sk-price"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ---- container: mirrors hv-main ---- */
.sk-main {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

/* ---- toolbar ---- */
.sk-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.sk-search {
  width: min(320px, 100%);
  height: 38px;
  border-radius: var(--radius-full);
}

.sk-sort-btn {
  width: 160px;
  height: 38px;
  margin-left: auto;
  flex-shrink: 0;
  border-radius: var(--radius-md);
}

/* ---- main layout ---- */
.sk-layout {
  display: flex;
  gap: 24px;
}

/* ---- sidebar ---- */
.sk-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 160px;
  flex-shrink: 0;
}

.sk-sidebar-item {
  height: 44px;
  border-radius: var(--radius-md);
}

/* ---- grid ---- */
.sk-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* staggered shimmer delay per card */
.sk-grid > :nth-child(1) .skeleton { animation-delay: 0s; }
.sk-grid > :nth-child(2) .skeleton { animation-delay: 0.08s; }
.sk-grid > :nth-child(3) .skeleton { animation-delay: 0.16s; }
.sk-grid > :nth-child(4) .skeleton { animation-delay: 0.04s; }
.sk-grid > :nth-child(5) .skeleton { animation-delay: 0.12s; }
.sk-grid > :nth-child(6) .skeleton { animation-delay: 0.2s; }

/* ---- card ---- */
.sk-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* top row */
.sk-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sk-card__badges {
  display: flex;
  gap: 6px;
}

.sk-badge {
  height: 20px;
  width: 52px;
  border-radius: var(--radius-full);
}

.sk-badge--narrow {
  width: 38px;
}

.sk-deadline {
  height: 14px;
  width: 80px;
  border-radius: var(--radius-sm);
}

/* title */
.sk-title {
  height: 20px;
  width: 75%;
  border-radius: var(--radius-sm);
  margin-top: 2px;
}

/* desc lines */
.sk-desc {
  height: 13px;
  width: 100%;
  border-radius: var(--radius-sm);
}

.sk-desc--short {
  width: 60%;
}

/* tags */
.sk-tags {
  display: flex;
  gap: 6px;
}

.sk-tag {
  height: 22px;
  width: 56px;
  border-radius: var(--radius-sm);
}

.sk-tag--wide {
  width: 76px;
}

/* footer */
.sk-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--c-border-light);
}

.sk-pub {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.sk-pub-label {
  height: 11px;
  width: 36px;
  border-radius: var(--radius-sm);
}

.sk-pub-name {
  height: 14px;
  width: 80px;
  border-radius: var(--radius-sm);
}

.sk-price {
  height: 24px;
  width: 52px;
  border-radius: var(--radius-sm);
}

/* ---- responsive ---- */
@media (max-width: 900px) {
  .sk-main {
    padding: 16px;
  }

  .sk-sidebar {
    display: none;
  }

  .sk-sort-btn {
    width: 38px;
    border-radius: 50%;
    margin-left: auto;
  }

  .sk-search {
    width: 100%;
  }

  .sk-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .sk-card {
    padding: 12px;
    gap: 6px;
  }

  .sk-card__top {
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
  }

  .sk-deadline {
    width: 70px;
  }

  .sk-title {
    height: 16px;
  }

  .sk-desc {
    height: 11px;
  }

  .sk-tags {
    display: none;
  }
}
</style>
