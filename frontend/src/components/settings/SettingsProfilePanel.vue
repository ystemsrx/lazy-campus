<script setup lang="ts">
import { ref } from "vue";
import type { UserMe } from "../../types/api";
import HomeAvatar from "../home/ui/HomeAvatar.vue";
import type { ProfileForm } from "../../composables/settings/types";

const props = defineProps<{
  active: boolean;
  me: UserMe | null;
  profileForm: ProfileForm;
  avatarUploading: boolean;
  paymentQrUploading: boolean;
  paymentQrDeleting: boolean;
}>();

const emit = defineEmits<{
  (e: "avatar-upload", event: Event): void;
  (e: "payment-qr-upload", event: Event): void;
  (e: "payment-qr-delete"): void;
}>();

const showQrLightbox = ref(false);
</script>

<template>
  <div class="sv-tab-pane" :class="{ 'sv-tab-pane--active': active }">
    <div class="sv-section-header">
      <h2 class="sv-section-title">个人资料</h2>
      <p class="sv-section-desc">更新您的头像和基本个人信息。</p>
    </div>

    <hr class="sv-divider" />

    <div class="sv-avatar-row">
      <div class="sv-avatar-wrap">
        <HomeAvatar
          size="xl"
          :avatar-url="props.me?.avatar_url"
          :gender="props.me?.gender ?? null"
          alt="avatar"
        />
        <label
          class="sv-avatar-overlay"
          :class="{ 'sv-avatar-overlay--show': props.avatarUploading }"
        >
          <svg
            v-if="!props.avatarUploading"
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
          >
            <path
              d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"
              stroke="white"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <circle cx="12" cy="13" r="4" stroke="white" stroke-width="1.8" />
          </svg>
          <div v-else class="sv-spinner sv-spinner--sm sv-spinner--white" />
          <input
            type="file"
            accept="image/*"
            hidden
            :disabled="props.avatarUploading"
            @change="emit('avatar-upload', $event)"
          />
        </label>
      </div>
      <div class="sv-avatar-info">
        <label class="sv-upload-btn">
          {{ props.avatarUploading ? "上传中..." : "更改头像" }}
          <input
            type="file"
            accept="image/*"
            hidden
            :disabled="props.avatarUploading"
            @change="emit('avatar-upload', $event)"
          />
        </label>
        <p class="sv-hint">支持 JPG、GIF 或 PNG 格式，最大 10MB</p>
      </div>
    </div>

    <div class="sv-grid-2">
      <div class="sv-field">
        <label class="sv-label">姓名</label>
        <div class="sv-input-wrap">
          <input
            class="sv-input sv-input--disabled"
            :value="props.me?.name"
            disabled
          />
          <svg
            class="sv-input-icon"
            width="15"
            height="15"
            viewBox="0 0 20 20"
            fill="none"
          >
            <circle
              cx="10"
              cy="10"
              r="8"
              stroke="currentColor"
              stroke-width="1.8"
            />
            <path
              d="M10 9v5M10 7v.5"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            />
          </svg>
        </div>
        <p class="sv-hint">姓名不可修改</p>
      </div>

      <div class="sv-field">
        <label class="sv-label sv-label--row">
          <span>昵称</span>
          <span
            class="sv-count"
            :class="{
              'sv-count--warn': props.profileForm.nickname.length >= 8,
            }"
          >
            {{ props.profileForm.nickname.length }}/8
          </span>
        </label>
        <input
          v-model="props.profileForm.nickname"
          class="sv-input"
          type="text"
          placeholder="请输入您的昵称"
          maxlength="8"
        />
      </div>

      <div class="sv-field sv-field--full">
        <label class="sv-label"
          >电子邮箱 <span class="sv-required">*</span></label
        >
        <input
          v-model.trim="props.profileForm.email"
          class="sv-input"
          type="email"
          placeholder="you@example.com"
          required
        />
      </div>

      <div class="sv-field">
        <label class="sv-label">性别 <span class="sv-required">*</span></label>
        <div class="sv-gender-toggle">
          <span
            class="sv-gender-indicator"
            :class="props.profileForm.gender === 'female' ? 'sv-gender-indicator--right' : ''"
          />
          <button
            v-for="g in ['male', 'female'] as const"
            :key="g"
            type="button"
            class="sv-gender-btn"
            :class="[
              props.profileForm.gender === g ? 'sv-gender-btn--active' : '',
              g === 'male' ? 'sv-gender-btn--male' : 'sv-gender-btn--female',
            ]"
            @click="props.profileForm.gender = g"
          >
            {{ g === "male" ? "♂ 男" : "♀ 女" }}
          </button>
        </div>
      </div>

      <div class="sv-field">
        <label class="sv-label">收款码</label>
        <div class="sv-qr-area">
          <div v-if="props.me?.payment_qr_url" class="sv-qr-preview-wrap">
            <img
              :src="props.me.payment_qr_url"
              alt="收款码"
              class="sv-qr-preview"
              @click="showQrLightbox = true"
            />
            <button
              type="button"
              class="sv-qr-delete-btn"
              :disabled="props.paymentQrDeleting"
              @click="emit('payment-qr-delete')"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                />
              </svg>
            </button>
          </div>
          <label
            v-else
            class="sv-qr-upload-trigger"
            :class="{ 'sv-qr-upload-trigger--busy': props.paymentQrUploading }"
          >
            <div
              v-if="props.paymentQrUploading"
              class="sv-spinner sv-spinner--sm"
            />
            <template v-else>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 5v14M5 12h14"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                />
              </svg>
              <span>上传</span>
            </template>
            <input
              type="file"
              accept="image/*"
              hidden
              :disabled="props.paymentQrUploading"
              @change="emit('payment-qr-upload', $event)"
            />
          </label>
        </div>
        <p class="sv-hint">上传后接取人可查看</p>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="sv-lightbox">
        <div
          v-if="showQrLightbox && props.me?.payment_qr_url"
          class="sv-lightbox-overlay"
          @click="showQrLightbox = false"
        >
          <img
            :src="props.me.payment_qr_url"
            class="sv-lightbox-img"
            alt="收款码大图"
          />
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped src="./settings-profile-panel.css"></style>
