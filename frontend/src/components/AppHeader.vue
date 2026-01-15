<template>
  <header class="header">
    <div class="logo" @click="goHome">
      <span class="logo-mark">L</span>
      <span>{{ t("brand.saas") }}</span>
    </div>
    <nav class="nav">
      <button class="ghost" @click="toggleTheme">{{ themeLabel }}</button>
      <button class="ghost" v-if="auth.user" @click="logout">{{ t("buttons.logout") }}</button>
    </nav>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const { t } = useI18n();
const auth = useAuthStore();
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

function goHome() {
  router.push("/");
}

function logout() {
  auth.logout();
  router.push("/");
}

onMounted(() => {
  auth.load();
  const saved = localStorage.getItem("theme");
  if (saved) {
    applyTheme(saved);
  } else {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
  }
});
</script>
