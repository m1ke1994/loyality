<template>
  <div class="panel">
    <h2>{{ t("labels.recentOperations") }}</h2>
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
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../api";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const ops = ref<any[]>([]);

onMounted(async () => {
  ops.value = await apiFetch(`/t/${tenant}/loyalty/ops`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
});
</script>
