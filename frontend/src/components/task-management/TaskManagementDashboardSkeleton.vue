<template>
  <div class="tm-dk-skeleton">
    <div class="tm-dk-sk-top">
      <div class="skeleton tm-dk-sk-role"></div>
      <div class="skeleton tm-dk-sk-role"></div>
    </div>

    <div class="tm-dk-sk-tabs-row">
      <div v-for="i in 3" :key="`dt-${i}`" class="skeleton tm-dk-sk-tab"></div>
    </div>

    <div class="tm-dk-sk-grid">
      <div v-for="i in 6" :key="`dk-${i}`" class="tm-dk-sk-card" :style="{ '--i': i - 1 }">
        <div class="tm-dk-sk-card__head">
          <div class="skeleton tm-dk-sk-card__icon"></div>
          <div class="tm-dk-sk-card__lines">
            <div class="skeleton" style="height:16px;width:70%"></div>
            <div class="skeleton" style="height:12px;width:50%"></div>
          </div>
        </div>
        <div class="skeleton" style="height:13px;width:90%"></div>
        <div class="skeleton" style="height:13px;width:60%"></div>
        <div class="tm-dk-sk-card__foot">
          <div class="skeleton" style="height:12px;width:80px"></div>
          <div class="skeleton" style="height:20px;width:52px"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="tm-tl-skeleton">
    <div class="tm-tl-sk-role-row">
      <div class="skeleton tm-tl-sk-role"></div>
      <div class="skeleton tm-tl-sk-role"></div>
    </div>

    <div class="tm-tl-sk-tabs">
      <div v-for="i in 3" :key="`tl-tab-${i}`" class="skeleton tm-tl-sk-tab"></div>
    </div>

    <div v-for="g in 3" :key="`group-${g}`" class="tm-tl-sk-group" :style="{ '--g': g - 1 }">
      <div class="tm-tl-sk-date">
        <div class="skeleton tm-tl-sk-num"></div>
        <div class="skeleton tm-tl-sk-dayname"></div>
      </div>

      <div class="tm-tl-sk-node">
        <div class="tm-tl-sk-line"></div>
        <div class="skeleton tm-tl-sk-dot"></div>
      </div>

      <div class="tm-tl-sk-cards">
        <div
          v-for="j in g === 2 ? 3 : 2"
          :key="`card-${g}-${j}`"
          class="tm-tl-sk-card"
          :style="{ '--j': j - 1 + (g - 1) * 2 }"
        >
          <div class="tm-tl-sk-card__top">
            <div class="tm-tl-sk-card__left">
              <div class="skeleton" style="height:17px;width:65%"></div>
              <div class="skeleton" style="height:13px;width:85%"></div>
            </div>
            <div class="skeleton tm-tl-sk-icon"></div>
          </div>
          <div class="tm-tl-sk-card__meta">
            <div class="skeleton" style="height:19px;width:50px;border-radius:9999px"></div>
            <div class="skeleton" style="height:14px;width:70px"></div>
            <div class="skeleton tm-tl-sk-price"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tm-dk-skeleton {
  display: block;
}

.tm-dk-sk-top {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}

.tm-dk-sk-role {
  height: 80px;
  border-radius: 20px;
}

.tm-dk-sk-tabs-row {
  display: flex;
  gap: 10px;
  margin-bottom: 28px;
  max-width: 560px;
}

.tm-dk-sk-tab {
  flex: 1;
  height: 44px;
  border-radius: 12px;
}

.tm-dk-sk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.tm-dk-sk-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 24px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tm-dk-sk-card .skeleton {
  animation-delay: calc(var(--i, 0) * 80ms);
}

.tm-dk-sk-card__head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 4px;
}

.tm-dk-sk-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  flex-shrink: 0;
}

.tm-dk-sk-card__lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tm-dk-sk-card__foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--c-border-light);
}

.tm-tl-skeleton {
  max-width: 800px;
  display: none;
}

.tm-tl-sk-role-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}

.tm-tl-sk-role {
  height: 80px;
  border-radius: 20px;
}

.tm-tl-sk-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 28px;
  max-width: 560px;
}

.tm-tl-sk-tab {
  flex: 1;
  height: 44px;
  border-radius: 12px;
}

.tm-tl-sk-group {
  display: grid;
  grid-template-columns: 80px 40px 1fr;
  gap: 0;
}

.tm-tl-sk-date {
  text-align: right;
  padding-right: 16px;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.tm-tl-sk-num {
  width: 40px;
  height: 32px;
  border-radius: 6px;
}

.tm-tl-sk-dayname {
  width: 48px;
  height: 13px;
}

.tm-tl-sk-node {
  position: relative;
  display: flex;
  justify-content: center;
}

.tm-tl-sk-line {
  position: absolute;
  top: 0;
  bottom: -48px;
  width: 2px;
  background: var(--c-border-light);
}

.tm-tl-sk-dot {
  position: relative;
  top: 20px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  z-index: 1;
}

.tm-tl-sk-cards {
  padding-left: 16px;
  padding-bottom: 48px;
  padding-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tm-tl-sk-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 16px;
  padding: 18px 20px;
}

.tm-tl-sk-card .skeleton {
  animation-delay: calc(var(--j, 0) * 80ms);
}

.tm-tl-sk-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.tm-tl-sk-card__left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.tm-tl-sk-card__meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tm-tl-sk-price {
  height: 15px;
  width: 44px;
  margin-left: auto;
}

.tm-tl-sk-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .tm-dk-skeleton {
    display: none;
  }

  .tm-tl-skeleton {
    display: block;
    max-width: none;
  }

  .tm-tl-sk-group {
    grid-template-columns: 44px 24px 1fr;
  }

  .tm-tl-sk-role-row {
    gap: 10px;
  }

  .tm-tl-sk-role {
    height: 66px;
    border-radius: 16px;
  }

  .tm-tl-sk-tabs {
    gap: 8px;
  }

  .tm-tl-sk-date {
    padding-right: 6px;
  }

  .tm-tl-sk-num {
    width: 28px;
    height: 24px;
  }

  .tm-tl-sk-dayname {
    width: 26px;
    height: 11px;
  }

  .tm-tl-sk-cards {
    padding-left: 8px;
    padding-bottom: 32px;
  }

  .tm-tl-sk-card {
    padding: 14px;
    border-radius: 14px;
    gap: 8px;
  }

  .tm-tl-sk-card__top {
    gap: 10px;
  }

  .tm-tl-sk-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
  }
}
</style>
