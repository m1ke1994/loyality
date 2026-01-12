<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("titles.cabinet") }}</h2>
      <div class="badge">{{ t("labels.points") }}: {{ points }}</div>
      <div class="grid two" style="margin-top: 12px;">
        <button @click="goQr">{{ t("buttons.showQr") }}</button>
        <button class="ghost" @click="reload">{{ t("buttons.refresh") }}</button>
      </div>
    </div>
    <div class="panel">
      <h3>{{ t("labels.recentOperations") }}</h3>
      <div class="list">
        <div v-for="op in ops" :key="op.id" class="list-item">
          <div>
            <div>{{ op.type }} ? {{ op.source }}</div>
            <div class="small">{{ op.created_at }}</div>
          </div>
          <div>
            <div>{{ op.points }} {{ t("labels.pointsShort") }}</div>
            <div class="small">{{ op.status }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../api";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const points = ref(0);
const ops = ref<any[]>([]);

async function reload() {
  const me = await apiFetch(`/${tenant}/client/me`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
  points.value = me.current_points;
  ops.value = await apiFetch(`/${tenant}/client/operations`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

function goQr() {
  router.push(`/t/${tenant}/qr`);
}

onMounted(() => {
  reload();
});
</script>
