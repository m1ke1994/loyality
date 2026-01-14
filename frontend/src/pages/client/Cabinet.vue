<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("titles.cabinet") }}</h2>
      <div class="badge">{{ t("labels.points") }}: {{ displayPoints }}</div>
      <div class="badge">{{ t("labels.tier") }}: {{ displayTier }}</div>
      <div class="grid two" style="margin-top: 12px;">
        <button @click="goQr">{{ t("buttons.showQr") }}</button>
        <button class="ghost" @click="reload">{{ t("buttons.refresh") }}</button>
      </div>
    </div>
    <div class="panel">
      <h3>{{ t("labels.recentOperations") }}</h3>
      <div v-if="ops.length === 0" class="small">{{ t("empty.operations") }}</div>
      <div v-else class="list">
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
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const points = ref<number | null>(null);
const tier = ref<string | null>(null);
const ops = ref<any[]>([]);

async function reload() {
  try {
    const me = await apiFetch(`/t/${tenant}/client/me`, {
      headers: { Authorization: `Bearer ${auth.tokens?.access}` },
    });
    points.value = typeof me?.current_points === "number" ? me.current_points : 0;
    tier.value = me?.tier ?? "-";
  } catch {
    points.value = 0;
    tier.value = "-";
  }

  try {
    ops.value = await apiFetch(`/t/${tenant}/client/operations`, {
      headers: { Authorization: `Bearer ${auth.tokens?.access}` },
    });
  } catch {
    ops.value = [];
  }
}

function goQr() {
  router.push(`/t/${tenant}/qr`);
}

onMounted(() => {
  reload();
});

const displayPoints = computed(() => points.value ?? 0);
const displayTier = computed(() => tier.value ?? "-");
</script>
