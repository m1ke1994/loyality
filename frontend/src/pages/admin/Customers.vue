<template>
  <div class="panel">
    <h2>{{ t("titles.customers") }}</h2>
    <div v-if="customers.length === 0" class="small">{{ t("empty.customers") }}</div>
    <div v-else class="list">
      <div v-for="customer in customers" :key="customer.id" class="list-item">
        <div>
          <div>{{ customer.email }}</div>
          <div class="small">{{ customer.phone || "-" }}</div>
        </div>
        <div>
          <div>{{ customer.tier }}</div>
          <div class="small">{{ customer.points }} {{ t("labels.pointsShort") }}</div>
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
const customers = ref<any[]>([]);

onMounted(async () => {
  customers.value = await apiFetch(`/t/${tenant}/admin/customers`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
});
</script>
