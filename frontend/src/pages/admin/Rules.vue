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
            <div class="small">
              {{ rule.applies_to_all ? t("rules.allClients") : t("rules.selectedClients", { count: rule.target_ids?.length || 0 }) }}
            </div>
          </div>
          <div class="list-actions">
            <div class="small">#{{ rule.id }}</div>
            <button class="ghost icon-button" @click="remove(rule.id)" aria-label="delete">x</button>
          </div>
        </div>
      </div>
    </div>
    <div class="panel grid">
      <h3>{{ t("sections.upsertRule") }}</h3>
      <div class="field-group">
        <input v-model.number="earnPercent" type="number" :placeholder="t('placeholders.earnPercent')" />
        <div class="field-help">{{ t("rules.helpEarnPercent") }}</div>
      </div>
      <div class="field-group">
        <input v-model.number="minAmount" type="number" :placeholder="t('placeholders.minAmount')" />
        <div class="field-help">{{ t("rules.helpMinAmount") }}</div>
      </div>
      <div class="grid">
        <div class="small">{{ t("rules.targetingLabel") }}</div>
        <div class="field-group">
          <select v-model="targetMode">
            <option value="all">{{ t("rules.allClients") }}</option>
            <option value="selected">{{ t("rules.selectClients") }}</option>
          </select>
          <div class="field-help">{{ t("rules.helpTargeting") }}</div>
        </div>
        <div v-if="targetMode === 'selected'" class="list">
          <label v-for="client in customers" :key="client.id" class="check-row">
            <input v-model="selectedClientIds" type="checkbox" :value="client.id" />
            <span>{{ client.email }}</span>
          </label>
          <div v-if="customers.length === 0" class="small">{{ t("empty.customers") }}</div>
        </div>
      </div>
      <button @click="upsert">{{ t("buttons.save") }}</button>
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
const rules = ref<any[]>([]);
const customers = ref<any[]>([]);
const earnPercent = ref(3);
const minAmount = ref(0);
const targetMode = ref("all");
const selectedClientIds = ref<number[]>([]);
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
  earnPercent.value = 3;
  minAmount.value = 0;
  targetMode.value = "all";
  selectedClientIds.value = [];
}

async function load() {
  rules.value = await apiFetch(`/t/${tenant}/admin/rules`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function loadCustomers() {
  customers.value = await apiFetch(`/t/${tenant}/admin/customers`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
}

async function upsert() {
  try {
    await apiFetch(`/t/${tenant}/admin/rules`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({
        location: null,
        earn_percent: earnPercent.value,
        min_amount: minAmount.value,
        rounding_mode: "FLOOR",
        bronze_threshold: 0,
        silver_threshold: 500,
        gold_threshold: 1500,
        applies_to_all: targetMode.value === "all",
        client_ids: targetMode.value === "selected" ? selectedClientIds.value : [],
      }),
    });
    showMessage(t("messages.saved"));
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
    await apiFetch(`/t/${tenant}/admin/rules/${id}`, {
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
  loadCustomers();
});
</script>
