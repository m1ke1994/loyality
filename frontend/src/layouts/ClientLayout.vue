<template>
  <div class="layout">
    <aside class="sidebar desktop-only">
      <div class="sidebar-brand" @click="goHome">{{ t("brand.client") }}</div>
      <nav class="sidebar-nav">
        <router-link :to="`/t/${tenant}/cabinet`">{{ t("menu.cabinet") }}</router-link>
        <router-link :to="`/t/${tenant}/qr`">{{ t("menu.qr") }}</router-link>
        <router-link :to="`/t/${tenant}/offers`">{{ t("menu.offers") }}</router-link>
        <router-link :to="`/t/${tenant}/history`">{{ t("menu.history") }}</router-link>
        <router-link :to="`/t/${tenant}/profile`">{{ t("menu.profile") }}</router-link>
      </nav>
    </aside>
    <div class="content">
      <header class="topbar">
        <div class="topbar-title desktop-only">{{ t("header.clientPortal") }}</div>
        <div class="topbar-actions desktop-only">
          <LanguageToggle />
          <button class="ghost" @click="toggleTheme">{{ themeLabel }}</button>
          <button class="ghost" v-if="isAuthenticated" @click="logout">{{ t("buttons.logout") }}</button>
        </div>
        <HeaderMobile class="mobile-only" :title="t('header.clientPortal')" @open="drawerOpen = true" />
      </header>
      <DrawerMenu
        :open="drawerOpen"
        :tenant="tenant"
        :title="t('brand.client')"
        :theme-label="themeLabel"
        :show-logout="isAuthenticated"
        @close="drawerOpen = false"
        @toggle-theme="toggleTheme"
        @logout="logout"
      />
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
import DrawerMenu from "../components/DrawerMenu.vue";
import HeaderMobile from "../components/HeaderMobile.vue";
import LanguageToggle from "../components/LanguageToggle.vue";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const theme = ref("light");
const drawerOpen = ref(false);
const isAuthenticated = computed(() => Boolean(auth.tokens?.access));

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
  router.push(`/t/${tenant}/login`);
  drawerOpen.value = false;
}

function goHome() {
  router.push(`/t/${tenant}/cabinet`);
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
