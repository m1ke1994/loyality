<template>
  <div class="lang-toggle" role="group" :aria-label="t('accessibility.languageToggle')">
    <button class="ghost" :class="{ active: locale === 'ru' }" @click="setLocale('ru')">RU</button>
    <span class="lang-divider">|</span>
    <button class="ghost" :class="{ active: locale === 'en' }" @click="setLocale('en')">EN</button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";

const { locale, t } = useI18n();

function setLocale(next: "ru" | "en") {
  if (locale.value === next) return;
  locale.value = next;
  localStorage.setItem("locale", next);
}
</script>
