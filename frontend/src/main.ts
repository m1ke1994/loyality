import { createApp } from "vue";
import { createPinia } from "pinia";
import { createI18n } from "vue-i18n";
import App from "./App.vue";
import router from "./router";
import ru from "./locales/ru.json";
import en from "./locales/en.json";
import "./styles.css";

const savedLocale = localStorage.getItem("locale");
const locale = savedLocale === "en" ? "en" : "ru";

const i18n = createI18n({
  legacy: false,
  locale,
  fallbackLocale: "ru",
  messages: { ru, en },
  globalInjection: true,
});

const app = createApp(App);
app.use(createPinia());
app.use(i18n);
app.use(router);
app.mount("#app");

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js");
  });
}
