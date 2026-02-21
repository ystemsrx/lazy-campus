<script setup lang="ts">
defineProps<{
  active: boolean
  name: string
  account: string
  password: string
  confirmPassword: string
  showPassword: boolean
}>()

const emit = defineEmits<{
  (e: 'update:name', value: string): void
  (e: 'update:account', value: string): void
  (e: 'update:password', value: string): void
  (e: 'update:confirmPassword', value: string): void
  (e: 'update:showPassword', value: boolean): void
  (e: 'submit'): void
}>()

function onNameInput(event: Event) {
  emit('update:name', (event.target as HTMLInputElement).value)
}

function onAccountInput(event: Event) {
  emit('update:account', (event.target as HTMLInputElement).value)
}

function onPasswordInput(event: Event) {
  emit('update:password', (event.target as HTMLInputElement).value)
}

function onConfirmPasswordInput(event: Event) {
  emit('update:confirmPassword', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <form
    class="av-form"
    :class="active ? 'av-form--active' : 'av-form--right'"
    @submit.prevent="emit('submit')"
  >
    <div class="av-input-group">
      <i class="fa-solid fa-id-card av-input-icon"></i>
      <input
        :value="name"
        type="text"
        placeholder="请输入真实姓名"
        class="av-input"
        required
        @input="onNameInput"
      />
    </div>
    <div class="av-input-group">
      <i class="fa-solid fa-user av-input-icon"></i>
      <input
        :value="account"
        type="text"
        placeholder="设置登录账号"
        class="av-input"
        required
        @input="onAccountInput"
      />
    </div>
    <div class="av-input-group">
      <i class="fa-solid fa-key av-input-icon"></i>
      <input
        :value="password"
        :type="showPassword ? 'text' : 'password'"
        placeholder="设置密码（至少6位）"
        class="av-input av-input--pw"
        minlength="6"
        required
        @input="onPasswordInput"
      />
      <button
        type="button"
        class="av-eye-btn"
        @click.prevent="emit('update:showPassword', !showPassword)"
      >
        <i :class="showPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
      </button>
    </div>
    <div class="av-input-group">
      <i class="fa-solid fa-lock av-input-icon"></i>
      <input
        :value="confirmPassword"
        type="password"
        placeholder="确认密码"
        class="av-input av-input--pw"
        minlength="6"
        required
        @input="onConfirmPasswordInput"
        @keyup.enter="emit('submit')"
      />
    </div>
  </form>
</template>

<style scoped src="./auth-form.css"></style>
