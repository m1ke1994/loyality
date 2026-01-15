<template>
  <div class="panel grid">
    <h2>{{ t("sections.bindPhone") }}</h2>
    <div class="field-group">
      <input v-model="phone" :placeholder="t('placeholders.phone')" />
      <div class="field-help">Телефон клиента для подтверждения и связи.</div>
    </div>
    <button @click="requestOtp">{{ t("buttons.requestOtp") }}</button>
    <div v-if="otp" class="badge">{{ t("labels.otp") }}: {{ otp }}</div>
    <div class="field-group">
      <input v-model="code" :placeholder="t('placeholders.phoneCode')" />
      <div class="field-help">Код из SMS для подтверждения номера.</div>
    </div>
    <button @click="confirmOtp">{{ t("buttons.confirm") }}</button>
    <p v-if="message" class="small">{{ message }}</p>
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
const phone = ref("");
const code = ref("");
const otp = ref("");
const message = ref("");

async function requestOtp() {
  message.value = "";
  otp.value = "";
  try {
    const data = await apiFetch(`/t/${tenant}/auth/phone/request`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({ phone: phone.value }),
    });
    otp.value = data.otp || "";
    message.value = t("messages.otpSent");
  } catch (err: any) {
    message.value = err.message;
  }
}

async function confirmOtp() {
  message.value = "";
  try {
    await apiFetch(`/t/${tenant}/auth/phone/confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({ code: code.value }),
    });
    router.push(`/t/${tenant}/cabinet`);
  } catch (err: any) {
    message.value = err.message;
  }
}
</script>
