<script setup lang="ts">
defineProps<{
  active: boolean
  account: string
  password: string
  showPassword: boolean
}>()

const emit = defineEmits<{
  (e: 'update:account', value: string): void
  (e: 'update:password', value: string): void
  (e: 'update:showPassword', value: boolean): void
  (e: 'submit'): void
}>()

function onAccountInput(event: Event) {
  emit('update:account', (event.target as HTMLInputElement).value)
}

function onPasswordInput(event: Event) {
  emit('update:password', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <form
    class="av-form"
    :class="active ? 'av-form--active' : 'av-form--left'"
    @submit.prevent="emit('submit')"
  >
    <div class="av-input-group">
      <i class="fa-solid fa-user av-input-icon"></i>
      <input
        :value="account"
        type="text"
        placeholder="办事大厅账号"
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
        placeholder="密码"
        class="av-input av-input--pw"
        required
        @input="onPasswordInput"
        @keyup.enter="emit('submit')"
      />
      <button
        type="button"
        class="av-eye-btn"
        @click.prevent="emit('update:showPassword', !showPassword)"
      >
        <i :class="showPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
      </button>
    </div>
  </form>
</template>

<style scoped src="./auth-form.css"></style>
