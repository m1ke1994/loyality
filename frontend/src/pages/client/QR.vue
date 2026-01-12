<template>
  <div class="panel grid">
    <h2>{{ t("titles.qr") }}</h2>
    <div class="qr-box">
      <canvas ref="canvas"></canvas>
    </div>
    <p class="small">{{ t("messages.qrRefresh") }}</p>
    <p v-if="error" class="small">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import QRCode from "qrcode";
import { apiFetch } from "../../api";
import { useAuthStore } from "../../stores/auth";

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const canvas = ref<HTMLCanvasElement | null>(null);
const error = ref("");
let timer: number | null = null;

async function issueQr() {
  error.value = "";
  try {
    const data = await apiFetch(`/${tenant}/client/qr/issue`, {
      method: "POST",
      headers: { Authorization: `Bearer ${auth.tokens?.access}` },
    });
    if (canvas.value) {
      await QRCode.toCanvas(canvas.value, data.qr_payload, { width: 220 });
    }
  } catch (err: any) {
    error.value = err.message;
  }
}

onMounted(() => {
  issueQr();
  timer = window.setInterval(issueQr, 5000);
});

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer);
  }
});
</script>
