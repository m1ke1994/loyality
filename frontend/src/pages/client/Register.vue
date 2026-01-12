<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.register") }}</h2>
    <div v-if="step === 'form'" class="grid">
      <input v-model="email" :placeholder="t('placeholders.email')" />
      <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
      <button @click="register">{{ t("buttons.createAccount") }}</button>
    </div>
    <div v-else class="grid">
      <p class="small">{{ t("messages.verificationSentTo", { email }) }}</p>
      <input v-model="code" :placeholder="t('placeholders.emailCode')" />
      <button @click="confirm">{{ t("buttons.confirmEmail") }}</button>
      <button class="ghost" @click="resend">{{ t("buttons.resendCode") }}</button>
    </div>
    <p v-if="message" class="small">{{ message }}</p>
    <p v-if="error" class="small">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../../api";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const tenant = route.params.tenant as string;
const email = ref("");
const password = ref("");
const code = ref("");
const message = ref("");
const error = ref("");
const step = ref<"form" | "verify">("form");

async function register() {
  error.value = "";
  message.value = "";
  try {
    await apiFetch(`/${tenant}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    step.value = "verify";
    message.value = t("messages.verificationCodeSent");
  } catch (err: any) {
    error.value = err.message;
  }
}

async function confirm() {
  error.value = "";
  message.value = "";
  try {
    await apiFetch(`/${tenant}/auth/email/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, code: code.value }),
    });
    message.value = t("messages.emailVerifiedLogin");
    router.push(`/t/${tenant}/login`);
  } catch (err: any) {
    error.value = err.message;
  }
}

async function resend() {
  error.value = "";
  message.value = "";
  try {
    await apiFetch(`/${tenant}/auth/email/request-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value }),
    });
    message.value = t("messages.codeResent");
  } catch (err: any) {
    error.value = err.message;
  }
}
</script>
