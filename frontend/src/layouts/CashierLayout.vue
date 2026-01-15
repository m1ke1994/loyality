<template>
  <div class="layout">
    <aside class="sidebar desktop-only">
      <div class="sidebar-brand" @click="goHome">{{ t("header.cashierPortal") }}</div>
      <nav class="sidebar-nav">
        <router-link :to="`/t/${tenant}/cashier/scan`">{{ t("menu.scan") }}</router-link>
        <router-link :to="`/t/${tenant}/cashier/operations`">{{ t("menu.operations") }}</router-link>
      </nav>
      <div class="sidebar-actions">
        <button class="ghost" @click="toggleTheme">{{ themeLabel }}</button>
        <button class="ghost" v-if="isAuthenticated" @click="logout">{{ t("buttons.logout") }}</button>
      </div>
    </aside>
    <div class="content">
      <header class="topbar">
        <div class="topbar-identity desktop-only">
          <div class="topbar-name">{{ displayName }}</div>
          <div class="topbar-org">{{ organizationLabel }}</div>
        </div>
        <HeaderMobile class="mobile-only" :title="t('header.cashierPortal')" @open="drawerOpen = true" />
      </header>
      <DrawerMenu
        :open="drawerOpen"
        :items="navItems"
        :title="t('header.cashierPortal')"
        :theme-label="themeLabel"
        :show-logout="isAuthenticated"
        :show-language="false"
        @close="drawerOpen = false"
        @toggle-theme="toggleTheme"
        @logout="logout"
      />
      <main class="page">
        <div v-if="noticeMessage" class="panel muted small">{{ noticeMessage }}</div>
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

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
const tenant = route.params.tenant as string;
const theme = ref("light");
const drawerOpen = ref(false);
const isAuthenticated = computed(() => Boolean(auth.tokens?.access));
const displayName = computed(() => {
  const first = (auth.user as { first_name?: string } | null)?.first_name || "";
  const last = (auth.user as { last_name?: string } | null)?.last_name || "";
  const full = `${last} ${first}`.trim();
  return full || auth.user?.email || t("header.cashierPortal");
});
const organizationLabel = computed(() => tenant);
const noticeMessage = computed(() =>
  route.query.notice === "forbidden" ? t("errors.forbidden") : ""
);
const navItems = computed(() => [
  { to: `/t/${tenant}/cashier/scan`, label: t("menu.scan") },
  { to: `/t/${tenant}/cashier/operations`, label: t("menu.operations") },
]);

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
  router.push(`/t/${tenant}/cashier/login`);
  drawerOpen.value = false;
}

function goHome() {
  router.push(`/t/${tenant}/cashier/scan`);
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
