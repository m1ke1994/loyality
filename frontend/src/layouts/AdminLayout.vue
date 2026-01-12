<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-brand" @click="goHome">{{ t("header.adminPortal") }}</div>
      <nav class="sidebar-nav">
        <router-link :to="`/t/${tenant}/admin/dashboard`">{{ t("menu.dashboard") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/customers`">{{ t("menu.customers") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/staff`">{{ t("menu.staff") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/locations`">{{ t("menu.locations") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/rules`">{{ t("menu.rules") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/operations`">{{ t("menu.operations") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/offers`">{{ t("menu.offers") }}</router-link>
        <router-link :to="`/t/${tenant}/admin/settings`">{{ t("menu.settings") }}</router-link>
      </nav>
    </aside>
    <div class="content">
      <header class="topbar">
        <div class="topbar-title">{{ t("header.adminPortal") }}</div>
        <div class="topbar-actions">
          <button class="ghost" @click="toggleTheme">{{ themeLabel }}</button>
          <button class="ghost" @click="logout">{{ t("buttons.logout") }}</button>
        </div>
      </header>
      <main class="page">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const theme = ref("light");

function applyTheme(next: string) {
  theme.value = next;
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
}

function toggleTheme() {
  applyTheme(theme.value === "light" ? "dark" : "light");
}

const themeLabel = computed(() =>
  theme.value === "light" ? t("buttons.darkTheme") : t("buttons.lightTheme")
);

function logout() {
  auth.logout();
  router.push(`/t/${tenant}/admin/login`);
}

function goHome() {
  router.push(`/t/${tenant}/admin/dashboard`);
}

onMounted(() => {
  const saved = localStorage.getItem("theme");
  if (saved) {
    applyTheme(saved);
  } else {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
  }
});
</script>
