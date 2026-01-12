<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.loginClient") }}</h2>
    <input v-model="email" :placeholder="t('placeholders.email')" />
    <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
    <button @click="login">{{ t("buttons.login") }}</button>
    <p class="small">
      {{ t("messages.noAccount") }}
      <router-link :to="`/t/${tenant}/register`">{{ t("buttons.register") }}</router-link>
    </p>
    <div v-if="needsVerify" class="panel muted">
      <p class="small">{{ t("messages.emailVerificationRequired") }}</p>
      <button class="ghost" @click="requestCode">{{ t("buttons.requestCode") }}</button>
      <input v-model="code" :placeholder="t('placeholders.emailCode')" />
      <button @click="confirmCode">{{ t("buttons.confirmEmail") }}</button>
    </div>
    <p v-if="error" class="small">{{ error }}</p>
    <p v-if="message" class="small">{{ message }}</p>
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
const email = ref("");
const password = ref("");
const code = ref("");
const error = ref("");
const message = ref("");
const needsVerify = ref(false);

async function login() {
  error.value = "";
  message.value = "";
  try {
    const data = await apiFetch(`/${tenant}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
    router.push(`/t/${tenant}/cabinet`);
  } catch (err: any) {
    if (err.message === "EMAIL_NOT_VERIFIED") {
      needsVerify.value = true;
    }
    error.value = err.message;
  }
}

async function requestCode() {
  message.value = "";
  try {
    await apiFetch(`/${tenant}/auth/email/request-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value }),
    });
    message.value = t("messages.codeSent");
  } catch (err: any) {
    error.value = err.message;
  }
}

async function confirmCode() {
  message.value = "";
  try {
    await apiFetch(`/${tenant}/auth/email/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, code: code.value }),
    });
    message.value = t("messages.emailVerifiedLogin");
    needsVerify.value = false;
  } catch (err: any) {
    error.value = err.message;
  }
}
</script>
