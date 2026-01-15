<template>
  <div class="panel grid small-form">
    <h2>{{ t("titles.adminLogin") }}</h2>
    <div class="field-group">
      <input v-model="email" :placeholder="t('placeholders.email')" />
      <div class="field-help">Email администратора для входа.</div>
    </div>
    <div class="field-group">
      <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
      <div class="field-help">Пароль учетной записи администратора.</div>
    </div>
    <button @click="login">{{ t("buttons.login") }}</button>
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
const email = ref("");
const password = ref("");
const error = ref("");

async function login() {
  error.value = "";
  try {
    const data = await apiFetch(`/t/${tenant}/auth/admin/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.value, password: password.value }),
    });
    if (data.user.role !== "ADMIN") {
      throw new Error(t("errors.forbidden"));
    }
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
    router.push(`/t/${tenant}/admin/dashboard`);
  } catch (err: any) {
    error.value = err.code === "ROLE_NOT_ALLOWED" ? t("errors.forbidden") : err.message;
  }
}
</script>
