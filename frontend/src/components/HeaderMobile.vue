<template>
  <div class="header-mobile">
    <button class="ghost menu-button" :aria-label="t('accessibility.openMenu')" @click="$emit('open')">
      ☰
    </button>
    <div class="header-mobile-title">
      <span class="brand-mark">L</span>
      <span>{{ title }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";

const { t } = useI18n();

defineProps<{ title: string }>();
defineEmits<{ (e: "open"): void }>();
</script>
