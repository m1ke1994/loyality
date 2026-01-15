<template>
  <div class="panel grid">
    <h2>{{ t("titles.register") }}</h2>
    <div class="field-group">
      <input v-model="lastName" :placeholder="t('placeholders.lastName')" />
    </div>
    <div class="field-group">
      <input v-model="firstName" :placeholder="t('placeholders.firstName')" />
    </div>
    <div class="field-group">
      <input v-model="email" :placeholder="t('placeholders.email')" />
      <div class="field-help">Email для входа и получения уведомлений.</div>
    </div>
    <div class="field-group">
      <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
      <div class="field-help">Придумайте надежный пароль от 8 символов.</div>
    </div>
    <button @click="register">{{ t("buttons.createAccount") }}</button>
    <p v-if="error" class="small">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../api";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const firstName = ref("");
const lastName = ref("");
const email = ref("");
const password = ref("");
const error = ref("");

async function register() {
  error.value = "";
  try {
    const data = await apiFetch(`/t/${tenant}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: firstName.value,
        last_name: lastName.value,
        email: email.value,
        password: password.value,
      }),
    });
    auth.setAuth({ user: data.user, tokens: data.tokens });
    router.push(`/t/${tenant}/bind-phone`);
  } catch (err: any) {
    error.value = err.message;
  }
}
</script>
