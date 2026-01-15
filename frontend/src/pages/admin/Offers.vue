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
            <div class="small">
              {{ offer.applies_to_all ? "Все клиенты" : `Выбрано клиентов: ${offer.target_ids?.length || 0}` }}
            </div>
          </div>
          <div class="badge">{{ offer.type }}</div>
        </div>
      </div>
    </div>
    <div class="panel grid">
      <h3>{{ t("sections.addOffer") }}</h3>
      <div class="field-group">
        <input v-model="title" :placeholder="t('placeholders.title')" />
        <div class="field-help">Короткое название, которое видит клиент.</div>
      </div>
      <div class="field-group">
        <input v-model="description" :placeholder="t('placeholders.description')" />
        <div class="field-help">Пояснение, какую выгоду дает предложение.</div>
      </div>
      <div class="field-group">
        <select v-model="type">
          <option value="BONUS">{{ t("filters.offerBonus") }}</option>
          <option value="MULTIPLIER">{{ t("filters.offerMultiplier") }}</option>
          <option value="COUPON">{{ t("filters.offerCoupon") }}</option>
        </select>
        <div class="field-help">Бонус — доп. баллы, Множитель — x к начислению, Купон — разовая скидка.</div>
      </div>
      <div class="field-group">
        <input v-model.number="multiplier" type="number" :placeholder="t('placeholders.multiplier')" />
        <div class="field-help">Коэффициент начисления баллов.</div>
      </div>
      <div class="field-group">
        <input v-model.number="bonus" type="number" :placeholder="t('placeholders.bonusPoints')" />
        <div class="field-help">Сколько дополнительных баллов начислить.</div>
      </div>
      <div class="grid">
        <div class="small">Аудитория предложения</div>
        <div class="field-group">
          <select v-model="targetMode">
            <option value="all">Все клиенты</option>
            <option value="selected">Выбрать клиентов</option>
          </select>
          <div class="field-help">Кому будет доступно предложение.</div>
        </div>
        <div v-if="targetMode === 'selected'" class="list">
          <label v-for="client in customers" :key="client.id" class="check-row">
            <input v-model="selectedClientIds" type="checkbox" :value="client.id" />
            <span>{{ client.email }}</span>
          </label>
          <div v-if="customers.length === 0" class="small">Нет клиентов для выбора.</div>
        </div>
      </div>
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
const targetMode = ref("all");
const customers = ref<any[]>([]);
const selectedClientIds = ref<number[]>([]);
const message = ref("");

async function load() {
  offers.value = await apiFetch(`/t/${tenant}/admin/offers`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function loadCustomers() {
  customers.value = await apiFetch(`/t/${tenant}/admin/customers`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function create() {
  message.value = "";
  await apiFetch(`/t/${tenant}/admin/offers`, {
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
      applies_to_all: targetMode.value === "all",
      client_ids: targetMode.value === "selected" ? selectedClientIds.value : [],
    }),
  });
  message.value = t("messages.created");
  await load();
}

onMounted(() => {
  load();
  loadCustomers();
});
</script>
