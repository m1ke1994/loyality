<template>
  <div class="widget">
    <div class="panel grid">
      <h3>{{ t("brand.widget") }}</h3>
      <p class="small">{{ t("widget.subtitle") }}</p>
      <div class="grid">
        <router-link :to="`/t/${tenant}/login`"><button>{{ t("buttons.login") }}</button></router-link>
        <router-link :to="`/t/${tenant}/register`"><button class="ghost">{{ t("buttons.register") }}</button></router-link>
        <router-link :to="`/t/${tenant}/qr`"><button>{{ t("buttons.showQr") }}</button></router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";

const route = useRoute();
const { t } = useI18n();
const tenant = route.params.tenant as string;
</script>

<style scoped>
.widget {
  padding: 16px;
  background: transparent;
}
</style>
