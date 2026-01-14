<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("titles.staff") }}</h2>
      <div v-if="staff.length === 0" class="small">{{ t("empty.staff") }}</div>
      <div v-else class="list">
        <div v-for="member in staff" :key="member.id" class="list-item">
          <div>
            <div>{{ member.email }}</div>
            <div class="small">{{ member.role }}</div>
          </div>
          <div>
            <div>{{ member.location }}</div>
            <div class="small">{{ member.active ? t("labels.active") : t("labels.disabled") }}</div>
          </div>
        </div>
      </div>
    </div>
    <div class="panel grid">
      <h3>{{ t("sections.addStaff") }}</h3>
      <input v-model="email" :placeholder="t('placeholders.email')" />
      <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
      <select v-model="role">
        <option value="CASHIER">{{ t("filters.roleCashier") }}</option>
        <option value="ADMIN">{{ t("filters.roleAdmin") }}</option>
      </select>
      <input v-model.number="locationId" type="number" :placeholder="t('placeholders.locationId')" />
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
const staff = ref<any[]>([]);
const email = ref("");
const password = ref("");
const role = ref("CASHIER");
const locationId = ref<number | null>(null);
const message = ref("");

async function load() {
  staff.value = await apiFetch(`/t/${tenant}/admin/staff`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function create() {
  message.value = "";
  await apiFetch(`/t/${tenant}/admin/staff`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.tokens?.access}`,
    },
    body: JSON.stringify({
      email: email.value,
      password: password.value,
      role: role.value,
      location_id: locationId.value,
    }),
  });
  message.value = t("messages.created");
  await load();
}

onMounted(() => {
  load();
});
</script>
