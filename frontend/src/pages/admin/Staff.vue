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
          <div class="list-actions">
            <div class="small">#{{ member.id }}</div>
            <button
              class="ghost icon-button"
              :disabled="isSelf(member.id)"
              @click="remove(member.id)"
              aria-label="delete"
            >
              x
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="panel grid">
      <h3>{{ t("sections.addStaff") }}</h3>
      <div class="field-group">
        <input v-model="lastName" :placeholder="t('placeholders.lastName')" />
      </div>
      <div class="field-group">
        <input v-model="firstName" :placeholder="t('placeholders.firstName')" />
      </div>
      <div class="field-group">
        <input v-model="email" :placeholder="t('placeholders.email')" />
        <div class="field-help">Email нового сотрудника.</div>
      </div>
      <div class="field-group">
        <input v-model="password" type="password" :placeholder="t('placeholders.password')" />
        <div class="field-help">Временный пароль для входа.</div>
      </div>
      <div class="field-group">
        <select v-model="role">
          <option value="CASHIER">{{ t("filters.roleCashier") }}</option>
          <option value="ADMIN">{{ t("filters.roleAdmin") }}</option>
        </select>
        <div class="field-help">Роль определяет доступ к разделам.</div>
      </div>
      <div v-if="locations.length === 0" class="small">
        {{ t("messages.addLocationsFirst") }}
      </div>
      <div class="field-group">
        <select v-model="locationId" :disabled="locations.length === 0">
          <option :value="null">{{ t("placeholders.locationNone") }}</option>
          <option v-for="loc in locations" :key="loc.id" :value="loc.id">
            {{ loc.name }} ({{ loc.address || "-" }})
          </option>
        </select>
        <div class="field-help">Привязка сотрудника к точке (необязательно).</div>
      </div>
      <button @click="create">{{ t("buttons.create") }}</button>
      <p v-if="message" class="notice success">{{ message }}</p>
      <p v-if="error" class="notice error">{{ error }}</p>
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
const staff = ref<any[]>([]);
const locations = ref<any[]>([]);
const email = ref("");
const firstName = ref("");
const lastName = ref("");
const password = ref("");
const role = ref("CASHIER");
const locationId = ref<number | null>(null);
const message = ref("");
const error = ref("");
const showConfirm = ref(false);
const pendingId = ref<number | null>(null);
let messageTimer: number | null = null;

async function load() {
  staff.value = await apiFetch(`/t/${tenant}/admin/staff`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
  locations.value = await apiFetch(`/t/${tenant}/admin/locations`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function create() {
  try {
    await apiFetch(`/t/${tenant}/admin/staff`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({
        first_name: firstName.value,
        last_name: lastName.value,
        email: email.value,
        password: password.value,
        role: role.value,
        location_id: locationId.value,
      }),
    });
    showMessage(t("messages.created"));
    resetForm();
    await load();
  } catch (err: any) {
    showError(err.message);
  }
}

function isSelf(id: number) {
  return id === auth.user?.id;
}

function remove(id: number) {
  if (isSelf(id)) {
    return;
  }
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
    await apiFetch(`/t/${tenant}/admin/staff/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${auth.tokens?.access}` },
    });
    showMessage(t("messages.deleted"));
    await load();
  } catch (err: any) {
    showError(err.message);
  }
}

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
  firstName.value = "";
  lastName.value = "";
  email.value = "";
  password.value = "";
  role.value = "CASHIER";
  locationId.value = null;
}

onMounted(() => {
  load();
});
</script>
