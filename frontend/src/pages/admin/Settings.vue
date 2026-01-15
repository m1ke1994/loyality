<template>
  <div class="panel grid">
    <h2>{{ t("titles.settings") }}</h2>
    <div class="field-group">
      <input v-model="brandColor" :placeholder="t('placeholders.brandColor')" />
      <div class="field-help">Основной цвет для оформления портала.</div>
    </div>
    <div class="field-group">
      <input v-model="emailFrom" :placeholder="t('placeholders.emailFrom')" />
      <div class="field-help">Адрес отправителя системных писем.</div>
    </div>
    <div class="field-group">
      <input v-model="logoUrl" :placeholder="t('placeholders.logoUrl')" />
      <div class="field-help">Ссылка на логотип компании.</div>
    </div>
    <button @click="save">{{ t("buttons.save") }}</button>
    <p v-if="message" class="notice success">{{ message }}</p>
    <p v-if="error" class="notice error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const brandColor = ref("");
const emailFrom = ref("");
const logoUrl = ref("");
const message = ref("");
const error = ref("");
let messageTimer: number | null = null;

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

async function load() {
  const data = await apiFetch(`/t/${tenant}/admin/settings`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
  brandColor.value = data.brand_color;
  emailFrom.value = data.email_from;
  logoUrl.value = data.logo_url;
}

async function save() {
  try {
    await apiFetch(`/t/${tenant}/admin/settings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({
        brand_color: brandColor.value,
        email_from: emailFrom.value,
        logo_url: logoUrl.value,
      }),
    });
    showMessage(t("messages.saved"));
  } catch (err: any) {
    showError(err.message);
  }
}

onMounted(() => {
  load();
});
</script>
