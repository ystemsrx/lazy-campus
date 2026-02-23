<script setup lang="ts">
import { proxyRefs } from 'vue'

import type { AdminUsersModel } from '../../composables/admin/useAdminUsers'
import AdminRadarChart from './AdminRadarChart.vue'
import AppDateTimePicker from '../AppDateTimePicker.vue'
import AppDropdown from '../AppDropdown.vue'

const props = defineProps<{
  model: AdminUsersModel
}>()

const vm = proxyRefs(props.model)

const genderOptions = [
  { value: '', label: '未设置' },
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
]

const roleOptions = [
  { value: 'user', label: '普通用户' },
  { value: 'admin', label: '管理员' },
]
</script>

<template>
  <Teleport to="body">
    <Transition name="aupd">
      <div v-if="vm.profileOpen" class="aupd-overlay" @mousedown.self="vm.closeUserProfile">
        <div class="aupd-drawer">
          <header class="aupd-header">
            <h3>用户 360 画像</h3>
            <button class="btn btn-ghost btn-sm" @click="vm.closeUserProfile">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </header>

          <div v-if="vm.profileLoading" class="aupd-loading">
            <div class="spinner"></div>
          </div>

          <template v-else-if="vm.selectedProfile">
            <section class="aupd-top">
              <img
                :src="vm.selectedProfile.avatar_url || 'https://placehold.co/120x120/e2e8f0/64748b?text=User'"
                class="aupd-avatar"
                alt="avatar"
              />
              <div class="aupd-top__meta">
                <h4>{{ vm.selectedProfile.display_name }}</h4>
                <p>#{{ vm.selectedProfile.id }} · {{ vm.selectedProfile.account }}</p>
                <div class="aupd-top__badges">
                  <span class="badge" :class="vm.selectedProfile.is_active ? 'badge-green' : 'badge-red'">
                    {{ vm.selectedProfile.is_active ? '活跃' : '停用' }}
                  </span>
                  <span class="badge" :class="vm.selectedProfile.is_banned ? 'badge-red' : 'badge-default'">
                    {{ vm.selectedProfile.is_banned ? '登录受限' : '登录正常' }}
                  </span>
                  <span class="badge badge-amber">封禁次数 {{ vm.selectedProfile.ban_count }}</span>
                </div>
              </div>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title">用户能力雷达</h5>
              <AdminRadarChart :metrics="vm.selectedProfile.radar" :size="250" />
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title">关键指标</h5>
              <div class="aupd-kpi">
                <div class="aupd-kpi__item">
                  <span>发布任务</span>
                  <strong>{{ vm.selectedProfile.published_task_count }}</strong>
                </div>
                <div class="aupd-kpi__item">
                  <span>接取任务</span>
                  <strong>{{ vm.selectedProfile.accepted_task_count }}</strong>
                </div>
                <div class="aupd-kpi__item">
                  <span>被举报</span>
                  <strong>{{ vm.selectedProfile.report_received_count }}</strong>
                </div>
                <div class="aupd-kpi__item">
                  <span>聊天消息</span>
                  <strong>{{ vm.selectedProfile.chat_message_count }}</strong>
                </div>
                <div class="aupd-kpi__item">
                  <span>发布者评分</span>
                  <strong>{{ vm.selectedProfile.publisher_rating_avg.toFixed(1) }}</strong>
                </div>
                <div class="aupd-kpi__item">
                  <span>接单者评分</span>
                  <strong>{{ vm.selectedProfile.worker_rating_avg.toFixed(1) }}</strong>
                </div>
              </div>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title">资料与风控编辑</h5>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">姓名</span>
                  <input v-model="vm.profileForm.name" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">昵称</span>
                  <input v-model="vm.profileForm.nickname" class="form-input" />
                </label>
              </div>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">邮箱</span>
                  <input v-model="vm.profileForm.email" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">角色</span>
                  <AppDropdown
                    v-model="vm.profileForm.role"
                    :options="roleOptions"
                    width="100%"
                    min-width="100%"
                  />
                </label>
              </div>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">性别</span>
                  <AppDropdown
                    v-model="vm.profileForm.gender"
                    :options="genderOptions"
                    width="100%"
                    min-width="100%"
                  />
                </label>
                <label class="form-group">
                  <span class="form-label">封禁截止时间</span>
                  <AppDateTimePicker
                    v-model="vm.profileForm.ban_until_local"
                    placeholder="设置解封时间"
                  />
                </label>
              </div>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">封禁次数</span>
                  <input v-model.number="vm.profileForm.ban_count" class="form-input" type="number" min="0" />
                </label>
                <label class="form-group">
                  <span class="form-label">被拉黑次数</span>
                  <input v-model.number="vm.profileForm.blocked_by_count" class="form-input" type="number" min="0" />
                </label>
              </div>
              <label class="form-group">
                <span class="form-label">封禁理由</span>
                <textarea v-model="vm.profileForm.ban_reason" class="form-textarea" />
              </label>

              <div class="aupd-check-grid">
                <label><input v-model="vm.profileForm.is_active" type="checkbox" /> 启用账号</label>
                <label><input v-model="vm.profileForm.is_banned" type="checkbox" /> 限制登录</label>
                <label><input v-model="vm.profileForm.ban_publish" type="checkbox" /> 禁止发布</label>
                <label><input v-model="vm.profileForm.ban_accept" type="checkbox" /> 禁止接单</label>
                <label><input v-model="vm.profileForm.ban_contact" type="checkbox" /> 禁止联系</label>
              </div>

              <div class="aupd-worker-title">接单档案</div>
              <div class="aupd-check-grid">
                <label><input v-model="vm.profileForm.worker_enabled" type="checkbox" /> 启用接单</label>
                <label><input v-model="vm.profileForm.worker_show_contact" type="checkbox" /> 公开联系方式</label>
              </div>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">技能 ID（逗号分隔）</span>
                  <input v-model="vm.profileForm.worker_skill_tag_ids_text" class="form-input" placeholder="例如 1,2,3" />
                </label>
                <label class="form-group">
                  <span class="form-label">微信</span>
                  <input v-model="vm.profileForm.worker_wechat" class="form-input" />
                </label>
              </div>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">最低报价</span>
                  <input v-model="vm.profileForm.worker_min_price" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">最高报价</span>
                  <input v-model="vm.profileForm.worker_max_price" class="form-input" />
                </label>
              </div>
              <label class="form-group">
                <span class="form-label">个人简介</span>
                <textarea v-model="vm.profileForm.worker_bio" class="form-textarea" />
              </label>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title">黑名单管理</h5>
              <div class="form-row">
                <label class="form-group">
                  <span class="form-label">用户 ID</span>
                  <input v-model="vm.blacklistAddUserId" class="form-input" placeholder="输入要拉黑的用户ID" />
                </label>
                <label class="form-group">
                  <span class="form-label">原因（可选）</span>
                  <input v-model="vm.blacklistAddReason" class="form-input" placeholder="原因说明" />
                </label>
              </div>
              <button class="btn btn-primary btn-sm" :disabled="vm.blacklistSubmitting" @click="vm.addBlacklistItem">
                {{ vm.blacklistSubmitting ? '处理中...' : '添加黑名单' }}
              </button>

              <div v-if="vm.blacklistLoading" class="aupd-blacklist-loading"><div class="spinner"></div></div>
              <div v-else-if="vm.blacklistItems.length === 0" class="aupd-blacklist-empty">当前黑名单为空</div>
              <div v-else class="aupd-blacklist-list">
                <div v-for="item in vm.blacklistItems" :key="item.blocked_user_id" class="aupd-blacklist-item">
                  <div>
                    <strong>#{{ item.blocked_user_id }} {{ item.blocked_display_name }}</strong>
                    <p>{{ item.reason || '无备注' }}</p>
                  </div>
                  <button class="btn btn-outline btn-sm" :disabled="vm.blacklistSubmitting" @click="vm.removeBlacklistItem(item.blocked_user_id)">
                    移除
                  </button>
                </div>
              </div>
            </section>
          </template>

          <footer class="aupd-footer">
            <button class="btn btn-outline btn-sm" @click="vm.closeUserProfile">关闭</button>
            <button class="btn btn-primary btn-sm" :disabled="vm.profileSaving" @click="vm.saveUserProfile">
              {{ vm.profileSaving ? '保存中...' : '保存用户变更' }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.aupd-overlay {
  position: fixed;
  inset: 0;
  z-index: 160;
  background: rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
}

.aupd-drawer {
  width: min(880px, 100vw);
  background: #f8fafc;
  height: 100vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-bottom: 82px;
}

.aupd-header {
  position: sticky;
  top: 0;
  z-index: 2;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.aupd-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
}

.aupd-loading {
  min-height: 220px;
  display: grid;
  place-items: center;
}

.aupd-top {
  margin: 0 16px;
  padding: 18px;
  border-radius: var(--radius-2xl);
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: var(--shadow-card);
  display: flex;
  align-items: center;
  gap: 14px;
}

.aupd-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255, 255, 255, 0.95);
}

.aupd-top__meta h4 {
  margin: 0;
}

.aupd-top__meta p {
  margin: 4px 0 8px;
  color: #94a3b8;
  font-size: 13px;
}

.aupd-top__badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.aupd-panel {
  margin: 0 16px;
  padding: 20px;
  border-radius: var(--radius-2xl) !important;
  border: 1px solid rgba(226, 232, 240, 0.6) !important;
  box-shadow: var(--shadow-card) !important;
}

.aupd-panel__title {
  margin: 0 0 10px;
}

.aupd-kpi {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.aupd-kpi__item {
  border-radius: var(--radius-lg);
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.6);
  padding: 12px;
}

.aupd-kpi__item span {
  color: #94a3b8;
  font-size: 12px;
  display: block;
}

.aupd-kpi__item strong {
  font-size: 22px;
  color: var(--c-text);
  letter-spacing: -0.02em;
}

.aupd-check-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.aupd-check-grid label {
  border: 1px solid rgba(226, 232, 240, 0.6);
  background: #f8fafc;
  border-radius: var(--radius-md);
  padding: 9px 10px;
  font-size: 13px;
  display: flex;
  gap: 6px;
  align-items: center;
  transition: background 200ms var(--ease);
}

.aupd-check-grid label:hover {
  background: #f1f5f9;
}

.aupd-worker-title {
  margin-top: 14px;
  font-weight: 600;
  color: var(--c-text);
}

.aupd-blacklist-empty {
  color: #6f8096;
  font-size: 13px;
  padding: 10px 0;
}

.aupd-blacklist-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.aupd-blacklist-item {
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-md);
  padding: 12px;
  background: #f8fafc;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.aupd-blacklist-item p {
  margin: 3px 0 0;
  color: #94a3b8;
  font-size: 12px;
}

.aupd-blacklist-loading {
  display: grid;
  place-items: center;
  padding: 12px;
}

.aupd-footer {
  position: fixed;
  right: 0;
  bottom: 0;
  width: min(880px, 100vw);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  padding: 14px 18px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  z-index: 5;
}

.aupd-enter-active,
.aupd-leave-active {
  transition: opacity 0.22s var(--ease);
}

.aupd-enter-from,
.aupd-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .aupd-kpi {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .aupd-check-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .aupd-kpi {
    grid-template-columns: 1fr;
  }

  .aupd-check-grid {
    grid-template-columns: 1fr;
  }
}
</style>
