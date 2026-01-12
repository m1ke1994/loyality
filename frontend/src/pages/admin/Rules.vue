<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("titles.rules") }}</h2>
      <div v-if="rules.length === 0" class="small">{{ t("empty.rules") }}</div>
      <div v-else class="list">
        <div v-for="rule in rules" :key="rule.id" class="list-item">
          <div>
            <div>{{ t("rules.earnLabel", { percent: rule.earn_percent }) }}</div>
            <div class="small">{{ t("rules.minLabel", { amount: rule.min_amount }) }}</div>
          </div>
          <div class="small">
            {{ t("rules.locationLabel", { location: rule.location || t("rules.tenant") }) }}
          </div>
        </div>
      </div>
    </div>
    <div class="panel grid">
      <h3>{{ t("sections.upsertRule") }}</h3>
      <input v-model.number="location" type="number" :placeholder="t('placeholders.locationOptional')" />
      <input v-model.number="earnPercent" type="number" :placeholder="t('placeholders.earnPercent')" />
      <input v-model.number="minAmount" type="number" :placeholder="t('placeholders.minAmount')" />
      <select v-model="rounding">
        <option value="FLOOR">{{ t("filters.floor") }}</option>
        <option value="ROUND">{{ t("filters.round") }}</option>
        <option value="CEIL">{{ t("filters.ceil") }}</option>
      </select>
      <input v-model.number="bronze" type="number" :placeholder="t('placeholders.bronzeThreshold')" />
      <input v-model.number="silver" type="number" :placeholder="t('placeholders.silverThreshold')" />
      <input v-model.number="gold" type="number" :placeholder="t('placeholders.goldThreshold')" />
      <button @click="upsert">{{ t("buttons.save") }}</button>
      <p class="small">{{ message }}</p>
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
const rules = ref<any[]>([]);
const location = ref<number | null>(null);
const earnPercent = ref(3);
const minAmount = ref(0);
const rounding = ref("FLOOR");
const bronze = ref(0);
const silver = ref(500);
const gold = ref(1500);
const message = ref("");

async function load() {
  rules.value = await apiFetch(`/${tenant}/admin/rules`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function upsert() {
  message.value = "";
  await apiFetch(`/${tenant}/admin/rules`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.tokens?.access}`,
    },
    body: JSON.stringify({
      location: location.value || null,
      earn_percent: earnPercent.value,
      min_amount: minAmount.value,
      rounding_mode: rounding.value,
      bronze_threshold: bronze.value,
      silver_threshold: silver.value,
      gold_threshold: gold.value,
    }),
  });
  message.value = t("messages.saved");
  await load();
}

onMounted(() => {
  load();
});
</script>
