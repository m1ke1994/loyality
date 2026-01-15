<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.loginClient") }}</h2>
    <div class="field-group">
      <input v-model="email" :placeholder="t('placeholders.email')" />
      <div class="field-help">Email, который вы использовали при регистрации.</div>
    </div>
    <div class="field-group">
      <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
      <div class="field-help">Пароль от вашего аккаунта.</div>
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
const error = ref("");
const message = ref("");
const needsVerify = ref(false);

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

function goVerify() {
  router.push({ path: `/t/${tenant}/verify-email`, query: { email: email.value } });
}
</script>
