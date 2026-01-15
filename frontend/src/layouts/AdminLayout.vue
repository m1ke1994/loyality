<template>
  <div class="layout">
    <aside class="sidebar desktop-only">
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
        <HeaderMobile
          class="mobile-only"
          :title="organizationLabel"
          :name="displayName"
          @open="drawerOpen = true"
        />
      </header>
      <DrawerMenu
        :open="drawerOpen"
        :items="navItems"
        :title="t('header.adminPortal')"
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
  return full || auth.user?.email || t("header.adminPortal");
});
const organizationLabel = computed(() => auth.user?.tenant_name || tenant);
const noticeMessage = computed(() =>
  route.query.notice === "forbidden" ? t("errors.forbidden") : ""
);
const navItems = computed(() => [
  { to: `/t/${tenant}/admin/dashboard`, label: t("menu.dashboard") },
  { to: `/t/${tenant}/admin/customers`, label: t("menu.customers") },
  { to: `/t/${tenant}/admin/staff`, label: t("menu.staff") },
  { to: `/t/${tenant}/admin/locations`, label: t("menu.locations") },
  { to: `/t/${tenant}/admin/rules`, label: t("menu.rules") },
  { to: `/t/${tenant}/admin/operations`, label: t("menu.operations") },
  { to: `/t/${tenant}/admin/offers`, label: t("menu.offers") },
  { to: `/t/${tenant}/admin/settings`, label: t("menu.settings") },
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
  router.push(`/t/${tenant}/admin/login`);
  drawerOpen.value = false;
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
