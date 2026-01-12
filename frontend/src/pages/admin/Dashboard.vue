<template>
  <div class="panel grid">
    <h2>{{ t("titles.dashboard") }}</h2>
    <div class="grid two">
      <div class="panel">
        <div class="small">{{ t("labels.clients") }}</div>
        <div class="stat">{{ stats.clients }}</div>
      </div>
      <div class="panel">
        <div class="small">{{ t("labels.staff") }}</div>
        <div class="stat">{{ stats.staff }}</div>
      </div>
      <div class="panel">
        <div class="small">{{ t("labels.locations") }}</div>
        <div class="stat">{{ stats.locations }}</div>
      </div>
      <div class="panel">
        <div class="small">{{ t("labels.operations") }}</div>
        <div class="stat">{{ stats.operations }}</div>
      </div>
    </div>
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
const stats = ref({ clients: 0, staff: 0, locations: 0, operations: 0 });

onMounted(async () => {
  stats.value = await apiFetch(`/${tenant}/admin/dashboard`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
});
</script>
