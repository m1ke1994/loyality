<template>
  <div class="panel hero">
    <h1>{{ t("brand.saas") }}</h1>
    <p class="small">{{ t("home.subtitle") }}</p>
    <div class="grid two">
      <div class="panel">
        <h3>{{ t("home.demoTenant") }}</h3>
        <p class="small">{{ t("home.slug") }}: demo</p>
        <div class="grid">
          <button @click="goClient">{{ t("home.clientPortal") }}</button>
          <button class="ghost" @click="goCashier">{{ t("home.cashierPortal") }}</button>
          <button class="ghost" @click="goAdmin">{{ t("home.adminPortal") }}</button>
        </div>
      </div>
      <div class="panel">
        <h3>{{ t("home.customTenant") }}</h3>
        <input v-model="tenant" :placeholder="t('placeholders.tenantSlug')" />
        <div class="grid">
          <button @click="goTenant">{{ t("buttons.go") }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

const router = useRouter();
const { t } = useI18n();
const tenant = ref("demo");

function goClient() {
  router.push(`/t/demo/login`);
}

function goCashier() {
  router.push(`/t/demo/cashier/login`);
}

function goAdmin() {
  router.push(`/t/demo/admin/login`);
}

function goTenant() {
  router.push(`/t/${tenant.value}/login`);
}
</script>
