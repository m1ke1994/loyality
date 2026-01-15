<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.loginClient") }}</h2>
    <div class="grid">
      <div class="field-group">
        <select v-model="authMode">
          <option value="email">{{ t("auth.email") }}</option>
          <option value="telegram">{{ t("auth.telegram") }}</option>
        </select>
      </div>
    </div>
    <div v-if="authMode === 'email'" class="grid">
      <div class="field-group">
        <input v-model="email" :placeholder="t('placeholders.email')" />
        <div class="field-help">{{ t("messages.loginEmailHelp") }}</div>
      </div>
      <div class="field-group">
        <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
        <div class="field-help">{{ t("messages.loginPasswordHelp") }}</div>
      </div>
      <button @click="login">{{ t("buttons.login") }}</button>
      <p class="small">
        {{ t("messages.noAccount") }}
        <router-link :to="`/t/${tenant}/register`">{{ t("buttons.register") }}</router-link>
      </p>
      <div v-if="needsVerify" class="panel muted">
        <p class="small">{{ t("messages.emailVerificationRequired") }}</p>
        <button class="ghost" @click="goVerify">{{ t("buttons.enterCode") }}</button>
      </div>
    </div>
    <div v-else class="grid">
      <div class="field-group">
        <input v-model="phone" :placeholder="t('placeholders.phone')" />
        <div class="field-help">{{ t("messages.telegramPhoneHelp") }}</div>
      </div>
      <button class="ghost" @click="openTelegram">{{ t("buttons.openTelegram") }}</button>
      <div class="field-group">
        <input v-model="code" :placeholder="t('placeholders.telegramCode')" />
      </div>
      <button @click="verifyTelegram">{{ t("buttons.confirm") }}</button>
    </div>
    <p v-if="error" class="notice error">{{ error }}</p>
    <p v-if="message" class="notice success">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const authMode = ref("email");
const email = ref("");
const password = ref("");
const phone = ref("");
const code = ref("");
const error = ref("");
const message = ref("");
const needsVerify = ref(false);
let messageTimer: number | null = null;

const telegramUsername = import.meta.env.VITE_TELEGRAM_BOT_USERNAME as string | undefined;

async function login() {
  error.value = "";
  message.value = "";
  needsVerify.value = false;
  try {
    const data = await apiFetch(`/t/${tenant}/auth/client/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
    router.push(`/t/${tenant}/cabinet`);
  } catch (err: any) {
    if (err.code === "EMAIL_NOT_VERIFIED") {
      needsVerify.value = true;
      message.value = t("messages.emailVerificationRequired");
    }
    error.value = err.code === "ROLE_NOT_ALLOWED" ? t("errors.forbidden") : err.message;
  }
}

function showMessage(text: string) {
  message.value = text;
  error.value = "";
  if (messageTimer) {
    window.clearTimeout(messageTimer);
  }
  messageTimer = window.setTimeout(() => {
    message.value = "";
  }, 3000);
}

function showError(text: string) {
  error.value = text;
  message.value = "";
  if (messageTimer) {
    window.clearTimeout(messageTimer);
  }
  messageTimer = window.setTimeout(() => {
    error.value = "";
  }, 3000);
}

async function openTelegram() {
  if (!telegramUsername) {
    showError(t("messages.telegramMissingBot"));
    return;
  }
  try {
    await apiFetch(`/t/${tenant}/auth/telegram/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: phone.value }),
    });
  } catch (err: any) {
    showError(err.message);
    return;
  }
  const link = `https://t.me/${telegramUsername}?start=${tenant}`;
  window.open(link, "_blank");
  showMessage(t("messages.telegramOpened"));
}

async function verifyTelegram() {
  error.value = "";
  message.value = "";
  try {
    const data = await apiFetch(`/t/${tenant}/auth/telegram/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: phone.value, code: code.value }),
    });
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
    router.push(`/t/${tenant}/cabinet`);
  } catch (err: any) {
    showError(err.message);
  }
}

function goVerify() {
  router.push({ path: `/t/${tenant}/verify-email`, query: { email: email.value } });
}
</script>
