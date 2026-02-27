<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import AppToast from "../components/AppToast.vue";
import LoginAppealModal from "../components/login/LoginAppealModal.vue";
import LoginForm from "../components/login/LoginForm.vue";
import RegisterForm from "../components/login/RegisterForm.vue";
import AuthSubmitButton from "../components/login/AuthSubmitButton.vue";
import { appAnonSlideCaptcha } from "../components/AppSlideCaptcha.vue";
import { useAppToast } from "../composables/useAppToast";
import { fetchRegistrationStatus, register } from "../api/auth";
import { useAuthStore } from "../stores/auth";
import { extractError } from "../utils/error";

const router = useRouter();
const auth = useAuthStore();

const appTitle = import.meta.env.VITE_APP_TITLE || "校园任务平台";

const isLogin = ref(true);
const showPassword = ref(false);

const account = ref("");
const password = ref("");
const regName = ref("");
const regAccount = ref("");
const regPassword = ref("");
const confirmPassword = ref("");
const showRegPassword = ref(false);

const { toast, showToast, clearToast } = useAppToast(3000);
const loading = ref(false);

const registrationEnabled = ref(false);
const registrationLoaded = ref(false);

const pageVisible = ref(false);

const showAppeal = ref(false);
const appealInitialBanUntil = ref<string | null>(null);

/** 每次页面加载生成一个 session_id，用于匿名验证码流程 */
function newSessionId(): string {
  return crypto.randomUUID().replace(/-/g, "");
}
const sessionId = ref(newSessionId());

function toggleForm() {
  isLogin.value = !isLogin.value;
  showPassword.value = false;
  showRegPassword.value = false;
  clearToast();
}

async function submitLogin() {
  clearToast();
  loading.value = true;
  try {
    const res = await auth.login(account.value, password.value);
    if (res.role === "admin") {
      await router.push("/admin");
      return;
    }
    await router.push(res.profile_completed ? "/home" : "/complete-profile");
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    if (detail && typeof detail === "object" && detail.code === "USER_BANNED") {
      appealInitialBanUntil.value = detail.ban_until || null;
      showAppeal.value = true;
      return;
    }

    // 后端要求验证码（密码错误次数过多）
    if (
      detail &&
      typeof detail === "object" &&
      detail.code === "CAPTCHA_REQUIRED"
    ) {
      const token = await appAnonSlideCaptcha("login", sessionId.value);
      if (!token) {
        // 用户取消了验证码
        showToast("请先完成验证", "error");
        return;
      }
      // 带验证码 token 重试一次
      try {
        const res2 = await auth.loginWithCaptcha(
          account.value,
          password.value,
          token,
          sessionId.value,
        );
        // 消耗后更换 session_id，避免复用
        sessionId.value = newSessionId();
        if (res2.role === "admin") {
          await router.push("/admin");
          return;
        }
        await router.push(res2.profile_completed ? "/home" : "/complete-profile");
      } catch (err2: any) {
        sessionId.value = newSessionId();
        const detail2 = err2?.response?.data?.detail;
        if (
          detail2 &&
          typeof detail2 === "object" &&
          detail2.code === "USER_BANNED"
        ) {
          appealInitialBanUntil.value = detail2.ban_until || null;
          showAppeal.value = true;
        } else {
          showToast(extractError(err2, "登录失败，请稍后重试"), "error");
        }
      }
      return;
    }

    showToast(extractError(error, "登录失败，请稍后重试"), "error");
  } finally {
    loading.value = false;
  }
}

async function submitRegister() {
  clearToast();

  if (!registrationEnabled.value) return;

  if (regPassword.value.length < 6) {
    showToast("密码至少 6 位", "error");
    return;
  }
  if (regPassword.value !== confirmPassword.value) {
    showToast("两次输入的密码不一致", "error");
    return;
  }

  // 注册时强制要求验证码
  const captchaToken = await appAnonSlideCaptcha("register", sessionId.value);
  if (!captchaToken) {
    showToast("请先完成验证", "error");
    return;
  }

  loading.value = true;
  try {
    const registerAccount = regAccount.value;
    const registerPassword = regPassword.value;
    await register({
      account: registerAccount,
      password: registerPassword,
      name: regName.value,
      captcha_token: captchaToken,
      session_id: sessionId.value,
    });
    // 注册成功后更换 session_id
    sessionId.value = newSessionId();
    const res = await auth.login(registerAccount, registerPassword);
    if (res.role === "admin") {
      await router.push("/admin");
      return;
    }
    await router.push(res.profile_completed ? "/home" : "/complete-profile");
  } catch (error: any) {
    sessionId.value = newSessionId();
    showToast(extractError(error, "注册失败，请稍后重试"), "error");
    loadRegistrationStatus();
  } finally {
    loading.value = false;
  }
}

async function loadRegistrationStatus() {
  try {
    const status = await fetchRegistrationStatus();
    registrationEnabled.value = status.registration_enabled;
  } catch {
    registrationEnabled.value = false;
  } finally {
    registrationLoaded.value = true;
  }
}

onMounted(() => {
  loadRegistrationStatus();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      pageVisible.value = true;
    });
  });
});
</script>

<template>
  <div class="av-page">
    <div class="av-bg">
      <div class="av-bg__orb av-bg__orb--tl"></div>
      <div class="av-bg__orb av-bg__orb--br"></div>
      <div class="av-bg__orb av-bg__orb--tr"></div>
    </div>

    <div class="av-outer" :class="{ 'av-outer--visible': pageVisible }">
      <div class="av-subtitle-wrap">
        <span
          class="av-subtitle"
          :class="isLogin ? 'av-subtitle--active' : 'av-subtitle--up'"
        >欢迎回来</span>
        <span
          class="av-subtitle"
          :class="!isLogin ? 'av-subtitle--active' : 'av-subtitle--down'"
        >加入我们</span>
      </div>

    <div class="av-card">
      <div class="av-header">
        <span class="av-brand">{{ appTitle }}</span>
        <div class="av-header__right">
          <button
            v-if="registrationLoaded && registrationEnabled"
            class="av-toggle"
            @click="toggleForm"
          >
            {{ isLogin ? "注册账号" : "直接登录" }}
          </button>
        </div>
      </div>

      <div class="av-title-wrap">
        <div
          class="av-title-row"
          :class="isLogin ? 'av-title-row--active' : 'av-title-row--up'"
        >
          <h1 class="av-title">登录</h1>
          <AppToast :toast="isLogin ? toast : null" inline />
        </div>
        <div
          class="av-title-row"
          :class="!isLogin ? 'av-title-row--active' : 'av-title-row--down'"
        >
          <h1 class="av-title">创建账号</h1>
          <AppToast :toast="!isLogin ? toast : null" inline />
        </div>
      </div>

      <div
        class="av-form-container"
        :class="
          isLogin ? 'av-form-container--login' : 'av-form-container--register'
        "
      >
        <LoginForm
          :active="isLogin"
          :account="account"
          :password="password"
          :show-password="showPassword"
          @update:account="account = $event"
          @update:password="password = $event"
          @update:show-password="showPassword = $event"
          @submit="submitLogin"
        />

        <RegisterForm
          :active="!isLogin"
          :name="regName"
          :account="regAccount"
          :password="regPassword"
          :confirm-password="confirmPassword"
          :show-password="showRegPassword"
          @update:name="regName = $event"
          @update:account="regAccount = $event"
          @update:password="regPassword = $event"
          @update:confirm-password="confirmPassword = $event"
          @update:show-password="showRegPassword = $event"
          @submit="submitRegister"
        />
      </div>

      <div class="av-footer">
        <div class="av-footer__text">
          <span class="av-footer__hint">请安全浏览！</span>
          <button class="av-browse-link" @click="router.push('/home')">
            随便看看 →
          </button>
        </div>
        <AuthSubmitButton
          :loading="loading"
          @click="isLogin ? submitLogin() : submitRegister()"
        />
      </div>
    </div>
    </div>

    <LoginAppealModal
      v-model="showAppeal"
      :account="account"
      :password="password"
      :initial-ban-until="appealInitialBanUntil"
    />
  </div>
</template>

<style scoped>
.av-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  font-family: var(--font-sans);
  overflow: hidden;
  background: #f3e7df;
}

.av-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}
.av-bg__orb {
  position: absolute;
  border-radius: 50%;
}
.av-bg__orb--tl {
  top: -15%;
  left: -10%;
  width: 50vw;
  height: 50vw;
  background: rgba(255, 255, 255, 0.6);
  filter: blur(100px);
  opacity: 0.8;
  mix-blend-mode: overlay;
}
.av-bg__orb--br {
  bottom: -10%;
  right: -5%;
  width: 60vw;
  height: 60vw;
  background: linear-gradient(
    to top left,
    rgba(240, 144, 80, 0.4),
    transparent
  );
  filter: blur(120px);
}
.av-bg__orb--tr {
  top: 20%;
  right: 15%;
  width: 20vw;
  height: 20vw;
  background: rgba(255, 255, 255, 0.5);
  filter: blur(60px);
}

.av-outer {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  max-width: 400px;
  opacity: 0;
  transform: translateY(32px) scale(0.97);
  transition:
    opacity 0.75s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.75s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-outer--visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.av-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.05);
  border-radius: 40px;
  padding: 32px 36px;
  transition: height 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}

.av-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 36px;
}
.av-brand {
  color: #6b7280;
  font-weight: 500;
  letter-spacing: 0.05em;
  font-size: 13px;
}
.av-header__right {
  min-width: 60px;
  text-align: right;
}
.av-toggle {
  background: none;
  border: none;
  color: #1f2937;
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
  padding: 0;
}
.av-toggle:hover {
  color: #000;
}

.av-subtitle-wrap {
  position: relative;
  height: 36px;
  width: 100%;
  margin-bottom: 14px;
  padding-left: 6px;
}
.av-subtitle {
  position: absolute;
  top: 0;
  left: 6px;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1;
  white-space: nowrap;
  background: linear-gradient(125deg, #1c1917 20%, #92400e 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  transition:
    opacity 0.6s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-subtitle--active {
  opacity: 1;
  transform: translateY(0);
}
.av-subtitle--up {
  opacity: 0;
  transform: translateY(-14px);
  pointer-events: none;
}
.av-subtitle--down {
  opacity: 0;
  transform: translateY(14px);
  pointer-events: none;
}

.av-title-wrap {
  position: relative;
  height: 48px;
  margin-bottom: 28px;
}
.av-title-row {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-title-row--active {
  opacity: 1;
  transform: translateY(0);
}
.av-title-row--up {
  opacity: 0;
  transform: translateY(-16px);
  pointer-events: none;
}
.av-title-row--down {
  opacity: 0;
  transform: translateY(16px);
  pointer-events: none;
}
.av-title {
  font-size: 32px;
  font-weight: 600;
  color: #111827;
  margin: 0;
  flex-shrink: 0;
}

.av-form-container {
  position: relative;
  transition: height 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-form-container--login {
  height: 120px;
}
.av-form-container--register {
  height: 232px;
}

.av-footer {
  margin-top: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.av-footer__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.av-footer__hint {
  font-size: 12px;
  color: #4b5563;
  font-weight: 500;
}
.av-browse-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #9ca3af;
  cursor: pointer;
  text-align: left;
  transition: color 0.2s;
}
.av-browse-link:hover {
  color: #6b7280;
  text-decoration: underline;
}

@media (max-width: 480px) {
  .av-card {
    border-radius: 28px;
    padding: 24px 24px;
  }
  .av-title {
    font-size: 28px;
  }
}
</style>
