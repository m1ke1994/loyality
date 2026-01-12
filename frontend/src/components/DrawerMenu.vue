<template>
  <div v-if="open" class="drawer-overlay" @click="close">
    <aside class="drawer" @click.stop>
      <div class="drawer-header">{{ title }}</div>
      <nav class="drawer-nav">
        <router-link :to="`/t/${tenant}/cabinet`" @click="close">{{ t("menu.cabinet") }}</router-link>
        <router-link :to="`/t/${tenant}/qr`" @click="close">{{ t("menu.qr") }}</router-link>
        <router-link :to="`/t/${tenant}/offers`" @click="close">{{ t("menu.offers") }}</router-link>
        <router-link :to="`/t/${tenant}/history`" @click="close">{{ t("menu.history") }}</router-link>
        <router-link :to="`/t/${tenant}/profile`" @click="close">{{ t("menu.profile") }}</router-link>
      </nav>
      <div class="drawer-footer">
        <LanguageToggle />
        <button class="ghost" @click="toggleTheme">{{ themeLabel }}</button>
        <button v-if="showLogout" class="ghost" @click="logout">{{ t("buttons.logout") }}</button>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import LanguageToggle from "./LanguageToggle.vue";

const { t } = useI18n();

defineProps<{
  open: boolean;
  tenant: string;
  title: string;
  themeLabel: string;
  showLogout: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "toggle-theme"): void;
  (e: "logout"): void;
}>();

function close() {
  emit("close");
}

function toggleTheme() {
  emit("toggle-theme");
}

function logout() {
  emit("logout");
  emit("close");
}
</script>
