<template>
  <div class="panel grid">
    <h2>{{ t("titles.settings") }}</h2>
    <input v-model="brandColor" :placeholder="t('placeholders.brandColor')" />
    <input v-model="emailFrom" :placeholder="t('placeholders.emailFrom')" />
    <input v-model="logoUrl" :placeholder="t('placeholders.logoUrl')" />
    <button @click="save">{{ t("buttons.save") }}</button>
    <p class="small">{{ message }}</p>
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

async function load() {
  const data = await apiFetch(`/t/${tenant}/admin/settings`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
  brandColor.value = data.brand_color;
  emailFrom.value = data.email_from;
  logoUrl.value = data.logo_url;
}

async function save() {
  message.value = "";
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
  message.value = t("messages.saved");
}

onMounted(() => {
  load();
});
</script>
