<template>
  <div class="panel grid">
    <div class="grid two">
      <select v-model="typeFilter">
        <option value="">{{ t("filters.all") }}</option>
        <option value="EARN">{{ t("filters.earn") }}</option>
        <option value="REDEEM">{{ t("filters.redeem") }}</option>
        <option value="REFUND">{{ t("filters.refund") }}</option>
      </select>
      <input v-model="receipt" :placeholder="t('placeholders.receiptId')" />
    </div>
    <div class="grid two">
      <input v-model="dateFrom" type="date" />
      <input v-model="dateTo" type="date" />
    </div>
    <button class="ghost" @click="load">{{ t("buttons.filter") }}</button>
    <div v-if="ops.length === 0" class="small">{{ t("empty.history") }}</div>
    <div v-else class="list">
      <div v-for="op in ops" :key="op.id" class="list-item">
        <div>
          <div>{{ op.type }} - {{ op.source }}</div>
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
const typeFilter = ref("");
const receipt = ref("");
const dateFrom = ref("");
const dateTo = ref("");

async function load() {
  const params = new URLSearchParams();
  if (typeFilter.value) params.set("type", typeFilter.value);
  if (receipt.value) params.set("receipt_id", receipt.value);
  if (dateFrom.value) params.set("from", dateFrom.value);
  if (dateTo.value) params.set("to", dateTo.value);
  const query = params.toString() ? `?${params.toString()}` : "";
  ops.value = await apiFetch(`/t/${tenant}/client/operations${query}`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

onMounted(() => {
  load();
});
</script>
