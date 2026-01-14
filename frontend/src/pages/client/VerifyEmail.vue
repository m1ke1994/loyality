<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.verifyEmail") }}</h2>
    <input v-model="email" :placeholder="t('placeholders.email')" />
    <input v-model="code" :placeholder="t('placeholders.emailCode')" />
    <button @click="verify" :disabled="busy">{{ t("buttons.confirmEmail") }}</button>
    <button class="ghost" @click="resend" :disabled="busy">{{ t("buttons.resendCode") }}</button>
    <p v-if="message" class="small">{{ message }}</p>
    <p v-if="error" class="small">{{ error }}</p>
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
const email = ref((route.query.email as string) || "");
const code = ref("");
const message = ref("");
const error = ref("");
const busy = ref(false);

async function verify() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const data = await apiFetch(`/${tenant}/auth/verify-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, code: code.value }),
    });
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
    router.push(`/t/${tenant}/cabinet`);
  } catch (err: any) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

async function resend() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    await apiFetch(`/${tenant}/auth/resend-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value }),
    });
    message.value = t("messages.codeSent");
  } catch (err: any) {
    error.value = err.message;
  } finally {
    busy.value = false;
  }
}

</script>
