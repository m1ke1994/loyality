<template>
  <div v-if="modelValue" class="modal-overlay" @click.self="close">
    <div class="modal">
      <div class="modal-title">{{ title }}</div>
      <div class="modal-body">{{ message }}</div>
      <div class="modal-actions">
        <button class="ghost" @click="close">{{ cancelText }}</button>
        <button @click="confirm">{{ confirmText }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type Props = {
  modelValue: boolean;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
};

const props = defineProps<Props>();
const emit = defineEmits<{
  (event: "update:modelValue", value: boolean): void;
  (event: "confirm"): void;
}>();

function close() {
  emit("update:modelValue", false);
}

function confirm() {
  emit("confirm");
  emit("update:modelValue", false);
}
</script>
