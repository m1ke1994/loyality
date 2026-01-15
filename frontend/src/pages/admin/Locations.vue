<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("titles.locations") }}</h2>
      <div v-if="locations.length === 0" class="small">{{ t("empty.locations") }}</div>
      <div v-else class="list">
        <div v-for="loc in locations" :key="loc.id" class="list-item">
          <div>
            <div>{{ loc.name }}</div>
            <div class="small">{{ loc.address || "-" }}</div>
          </div>
          <div class="small">#{{ loc.id }}</div>
        </div>
      </div>
    </div>
    <div class="panel grid">
      <h3>{{ t("sections.addLocation") }}</h3>
      <div class="field-group">
        <input v-model="name" :placeholder="t('placeholders.name')" />
        <div class="field-help">Название точки, например “Центр”.</div>
      </div>
      <div class="field-group">
        <input v-model="address" :placeholder="t('placeholders.address')" />
        <div class="field-help">Адрес или ориентир для сотрудников.</div>
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
const locations = ref<any[]>([]);
const name = ref("");
const address = ref("");
const message = ref("");

async function load() {
  locations.value = await apiFetch(`/t/${tenant}/admin/locations`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function create() {
  message.value = "";
  await apiFetch(`/t/${tenant}/admin/locations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.tokens?.access}`,
    },
    body: JSON.stringify({ name: name.value, address: address.value }),
  });
  message.value = t("messages.created");
  await load();
}

onMounted(() => {
  load();
});
</script>
