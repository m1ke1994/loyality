<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.register") }}</h2>
    <div class="grid">
      <div class="field-group">
        <input v-model="email" :placeholder="t('placeholders.email')" />
        <div class="field-help">Email для входа и подтверждения.</div>
      </div>
      <div class="field-group">
        <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
        <div class="field-help">Придумайте пароль от 8 символов.</div>
      </div>
      <div class="field-group">
        <input v-model="password2" type="password" :placeholder="t('placeholders.passwordRepeat')" />
        <div class="field-help">Повторите пароль без ошибок.</div>
      </div>
      <button @click="register">{{ t("buttons.createAccount") }}</button>
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
const password2 = ref("");
const message = ref("");
const error = ref("");

async function register() {
  error.value = "";
  message.value = "";
  try {
    await apiFetch(`/t/${tenant}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, password: password.value, password2: password2.value }),
    });
    message.value = t("messages.verificationCodeSent");
    router.push({ path: `/t/${tenant}/verify-email`, query: { email: email.value } });
  } catch (err: any) {
    error.value = err.message;
  }
}
</script>
