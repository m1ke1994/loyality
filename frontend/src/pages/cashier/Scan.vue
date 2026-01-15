<template>
  <div class="grid">
    <div class="panel">
      <h2>{{ t("menu.scan") }}</h2>
      <video ref="video" class="qr-video"></video>
      <div class="grid" style="margin-top: 12px;">
        <div class="field-group">
          <input v-model="manualToken" :placeholder="t('placeholders.qrPayload')" />
          <div class="field-help">Введите токен QR, если сканер недоступен.</div>
        </div>
        <button class="ghost" @click="manualValidate">{{ t("buttons.validate") }}</button>
      </div>
      <p v-if="error" class="small">{{ error }}</p>
    </div>
    <div class="panel" v-if="card">
      <h3>{{ t("labels.client") }}</h3>
      <div class="small">{{ t("labels.email") }}: {{ card.client_email }}</div>
      <div class="small">{{ t("labels.phone") }}: {{ card.client_phone }}</div>
      <div class="badge">{{ t("labels.tier") }}: {{ card.tier }}</div>
      <div class="badge">{{ t("labels.currentPoints") }}: {{ card.current_points }}</div>
      <div class="field-group">
        <input v-model.number="amount" type="number" :placeholder="t('placeholders.amount')" />
        <div class="field-help">Сумма покупки клиента.</div>
      </div>
      <div class="field-group">
        <input v-model="receiptId" :placeholder="t('placeholders.receiptId')" />
        <div class="field-help">Номер чека для учета и возврата.</div>
      </div>
      <div class="grid two">
        <button @click="earn">{{ t("buttons.earn") }}</button>
        <button class="ghost" @click="redeem">{{ t("buttons.redeem") }}</button>
      </div>
      <div class="grid">
        <button class="ghost" @click="refund">{{ t("buttons.refundByReceipt") }}</button>
      </div>
      <p v-if="message" class="small">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import QrScanner from "qr-scanner";
import qrWorker from "qr-scanner/qr-scanner-worker.min.js?url";
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";

QrScanner.WORKER_PATH = qrWorker;

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const video = ref<HTMLVideoElement | null>(null);
const scanner = ref<QrScanner | null>(null);
const manualToken = ref("");
const error = ref("");
const message = ref("");
const amount = ref(0);
const receiptId = ref("");
const lastToken = ref("");
const card = ref<any>(null);

async function validate(token: string) {
  error.value = "";
  try {
    const data = await apiFetch(`/t/${tenant}/loyalty/qr/validate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({ qr_payload: token }),
    });
    card.value = data;
    lastToken.value = token;
  } catch (err: any) {
    error.value = err.message;
  }
}

async function manualValidate() {
  if (!manualToken.value) return;
  await validate(manualToken.value);
}

async function earn() {
  await submit("earn");
}

async function redeem() {
  await submit("redeem");
}

async function refund() {
  message.value = "";
  try {
    const data = await apiFetch(`/t/${tenant}/loyalty/points/refund`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({
        receipt_id: receiptId.value,
        idempotency_key: crypto.randomUUID(),
      }),
    });
    message.value = t("messages.refundSuccess", {
      points: data.points,
      balance: data.current_points,
    });
  } catch (err: any) {
    message.value = err.message;
  }
}

async function submit(action: "earn" | "redeem") {
  message.value = "";
  if (!lastToken.value) return;
  const idempotency = crypto.randomUUID();
  try {
    const data = await apiFetch(`/t/${tenant}/loyalty/points/${action}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${auth.tokens?.access}`,
      },
      body: JSON.stringify({
        qr_payload: lastToken.value,
        amount: amount.value,
        idempotency_key: idempotency,
        receipt_id: receiptId.value || undefined,
      }),
    });
    message.value = t("messages.earnSuccess", {
      points: data.points,
      balance: data.current_points,
    });
  } catch (err: any) {
    message.value = err.message;
  }
}

onMounted(async () => {
  if (!video.value) return;
  scanner.value = new QrScanner(video.value, (result) => {
    const token = result.data;
    validate(token);
  });
  await scanner.value.start();
});

onBeforeUnmount(() => {
  scanner.value?.stop();
  scanner.value?.destroy();
});
</script>

<style scoped>
.qr-video {
  width: 100%;
  max-width: 360px;
  border-radius: 12px;
  border: 1px solid var(--border);
}
</style>
