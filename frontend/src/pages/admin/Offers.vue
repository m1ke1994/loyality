<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("titles.offersAdmin") }}</h2>
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
    <div class="panel grid">
      <h3>{{ t("sections.addOffer") }}</h3>
      <input v-model="title" :placeholder="t('placeholders.title')" />
      <input v-model="description" :placeholder="t('placeholders.description')" />
      <select v-model="type">
        <option value="BONUS">{{ t("filters.offerBonus") }}</option>
        <option value="MULTIPLIER">{{ t("filters.offerMultiplier") }}</option>
        <option value="COUPON">{{ t("filters.offerCoupon") }}</option>
      </select>
      <input v-model.number="multiplier" type="number" :placeholder="t('placeholders.multiplier')" />
      <input v-model.number="bonus" type="number" :placeholder="t('placeholders.bonusPoints')" />
      <button @click="create">{{ t("buttons.create") }}</button>
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
const offers = ref<any[]>([]);
const title = ref("");
const description = ref("");
const type = ref("BONUS");
const multiplier = ref(1);
const bonus = ref(0);
const message = ref("");

async function load() {
  offers.value = await apiFetch(`/${tenant}/admin/offers`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function create() {
  message.value = "";
  await apiFetch(`/${tenant}/admin/offers`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.tokens?.access}`,
    },
    body: JSON.stringify({
      title: title.value,
      description: description.value,
      type: type.value,
      multiplier: multiplier.value,
      bonus_points: bonus.value,
      is_active: true,
    }),
  });
  message.value = t("messages.created");
  await load();
}

onMounted(() => {
  load();
});
</script>
