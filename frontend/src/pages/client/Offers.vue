<template>
  <div class="panel">
    <h2>{{ t("titles.offers") }}</h2>
    <div v-if="offers.length === 0" class="small">{{ t("empty.offers") }}</div>
    <div v-else class="list">
      <div v-for="offer in offers" :key="offer.id" class="list-item">
        <div>
          <div>{{ offer.title }}</div>
          <div class="small">{{ offer.description }}</div>
        </div>
        <div class="badge">{{ offer.type }}</div>
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
const offers = ref<any[]>([]);

onMounted(async () => {
  offers.value = await apiFetch(`/t/${tenant}/client/offers`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
});
</script>
