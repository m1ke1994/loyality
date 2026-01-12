<template>
  <div class="panel grid">
    <div class="grid two">
      <input v-model="receiptSearch" :placeholder="t('placeholders.receiptSearch')" />
      <button class="ghost" @click="load">{{ t("buttons.search") }}</button>
    </div>
    <div v-if="ops.length === 0" class="small">{{ t("empty.operations") }}</div>
    <div v-else class="list">
      <div v-for="op in ops" :key="op.id" class="list-item">
        <div>
          <div>{{ op.type }} ? {{ op.source }}</div>
          <div class="small">{{ op.receipt_id || "-" }}</div>
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
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const ops = ref<any[]>([]);
const receiptSearch = ref("");

async function load() {
  const query = receiptSearch.value ? `?receipt_id=${encodeURIComponent(receiptSearch.value)}` : "";
  ops.value = await apiFetch(`/${tenant}/admin/operations${query}`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

onMounted(() => {
  load();
});
</script>
