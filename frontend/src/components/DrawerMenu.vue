<template>
  <div v-if="open" class="drawer-overlay" @click="close">
    <aside class="drawer" @click.stop>
      <div class="drawer-header">{{ title }}</div>
      <nav class="drawer-nav">
        <router-link v-for="item in items" :key="item.to" :to="item.to" @click="close">
          {{ item.label }}
        </router-link>
      </nav>
      <div class="drawer-footer">
        <LanguageToggle v-if="showLanguage" />
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

type DrawerItem = {
  to: string;
  label: string;
};

withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    items: DrawerItem[];
    themeLabel: string;
    showLogout: boolean;
    showLanguage?: boolean;
  }>(),
  {
    showLanguage: true,
  }
);

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
