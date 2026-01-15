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
          <div class="list-actions">
            <div class="small">#{{ loc.id }}</div>
            <button class="ghost icon-button" @click="remove(loc.id)" aria-label="delete">x</button>
          </div>
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
      <p v-if="message" class="small">{{ message }}</p>
      <p v-if="error" class="small">{{ error }}</p>
    </div>
    <ConfirmModal
      v-model="showConfirm"
      :title="t('buttons.confirm')"
      :message="t('messages.confirmDelete')"
      :confirm-text="t('common.yes')"
      :cancel-text="t('common.no')"
      @confirm="confirmRemove"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";
import ConfirmModal from "../../components/ConfirmModal.vue";

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const locations = ref<any[]>([]);
const name = ref("");
const address = ref("");
const message = ref("");
const error = ref("");
const showConfirm = ref(false);
const pendingId = ref<number | null>(null);
let messageTimer: number | null = null;

function showMessage(text: string) {
  message.value = text;
  error.value = "";
  if (messageTimer) {
    window.clearTimeout(messageTimer);
  }
  messageTimer = window.setTimeout(() => {
    message.value = "";
  }, 3000);
}

function showError(text: string) {
  error.value = text;
  message.value = "";
  if (messageTimer) {
    window.clearTimeout(messageTimer);
  }
  messageTimer = window.setTimeout(() => {
    error.value = "";
  }, 3000);
}

function resetForm() {
  name.value = "";
  address.value = "";
}

async function load() {
  locations.value = await apiFetch(`/t/${tenant}/admin/locations`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function create() {
  try {
    await apiFetch(`/t/${tenant}/admin/locations`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({ name: name.value, address: address.value }),
    });
    showMessage(t("messages.created"));
    resetForm();
    await load();
  } catch (err: any) {
    showError(err.message);
  }
}

function remove(id: number) {
  pendingId.value = id;
  showConfirm.value = true;
}

async function confirmRemove() {
  if (pendingId.value == null) {
    return;
  }
  const id = pendingId.value;
  pendingId.value = null;
  try {
    await apiFetch(`/t/${tenant}/admin/locations/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${auth.tokens?.access}` },
    });
    showMessage(t("messages.deleted"));
    await load();
  } catch (err: any) {
    showError(err.message);
  }
}

onMounted(() => {
  load();
});
</script>

