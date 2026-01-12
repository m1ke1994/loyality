<template>
  <div class="header-mobile">
    <button class="ghost burger" :aria-label="t('accessibility.openMenu')" @click="$emit('open')">☰</button>
    <div class="header-mobile-title">{{ title }}</div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";

const { t } = useI18n();

defineProps<{ title: string }>();
defineEmits<{ (e: "open"): void }>();
</script>
