<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.register") }}</h2>
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
        <input v-model="lastName" :placeholder="t('placeholders.lastName')" />
      </div>
      <div class="field-group">
        <input v-model="firstName" :placeholder="t('placeholders.firstName')" />
      </div>
      <div class="field-group">
        <input v-model="email" :placeholder="t('placeholders.email')" />
        <div class="field-help">{{ t("messages.registerEmailHelp") }}</div>
      </div>
      <div class="field-group">
        <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
        <div class="field-help">{{ t("messages.registerPasswordHelp") }}</div>
      </div>
      <div class="field-group">
        <input v-model="password2" type="password" :placeholder="t('placeholders.passwordRepeat')" />
        <div class="field-help">{{ t("messages.registerPasswordRepeatHelp") }}</div>
      </div>
      <button @click="register">{{ t("buttons.createAccount") }}</button>
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
    <p v-if="message" class="notice success">{{ message }}</p>
    <p v-if="error" class="notice error">{{ error }}</p>
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
const firstName = ref("");
const lastName = ref("");
const email = ref("");
const password = ref("");
const password2 = ref("");
const phone = ref("");
const code = ref("");
const message = ref("");
const error = ref("");
const telegramNonce = ref("");
let messageTimer: number | null = null;

const telegramUsername = import.meta.env.VITE_TELEGRAM_BOT_USERNAME as string | undefined;

function normalizeTelegramUsername(raw: string | undefined) {
  if (!raw) {
    return "";
  }
  const trimmed = raw.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.startsWith("@") ? trimmed.slice(1) : trimmed;
}

async function getTelegramUsername() {
  const fromEnv = normalizeTelegramUsername(telegramUsername);
  if (fromEnv) {
    return fromEnv;
  }
  try {
    const data = await apiFetch(`/t/${tenant}/auth/telegram/config`);
    if (data?.configured && data?.bot_username) {
      return normalizeTelegramUsername(data.bot_username);
    }
    showError(t("messages.telegramMissingBot"));
    return "";
  } catch (err: any) {
    showError(err.message);
    return "";
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

async function register() {
  error.value = "";
  message.value = "";
  try {
    await apiFetch(`/t/${tenant}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: firstName.value,
        last_name: lastName.value,
        email: email.value,
        password: password.value,
        password2: password2.value,
      }),
    });
    showMessage(t("messages.verificationCodeSent"));
    router.push({ path: `/t/${tenant}/verify-email`, query: { email: email.value } });
  } catch (err: any) {
    showError(err.message);
  }
}

async function openTelegram() {
  const resolvedUsername = await getTelegramUsername();
  if (!resolvedUsername) {
    return;
  }
  try {
    const data = await apiFetch(`/t/${tenant}/auth/telegram/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: phone.value }),
    });
    telegramNonce.value = data?.nonce || "";
    const startPayload = data?.start_payload || tenant;
    const link = `https://t.me/${resolvedUsername}?start=${encodeURIComponent(startPayload)}`;
    window.open(link, "_blank");
    showMessage(t("messages.telegramOpened"));
    return;
  } catch (err: any) {
    if (err.code === "TELEGRAM_NOT_CONFIGURED") {
      showError(t("messages.telegramMissingBot"));
      return;
    }
    showError(err.message);
    return;
  }
}

async function verifyTelegram() {
  error.value = "";
  message.value = "";
  try {
    const payload: Record<string, string> = {
      phone: phone.value,
      code: code.value,
    };
    if (telegramNonce.value) {
      payload.nonce = telegramNonce.value;
    }
    const data = await apiFetch(`/t/${tenant}/auth/telegram/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
    router.push(`/t/${tenant}/profile`);
  } catch (err: any) {
    showError(err.message);
  }
}
</script>
