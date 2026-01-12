import { createRouter, createWebHistory, type RouteLocationNormalized } from "vue-router";
import Home from "../pages/Home.vue";
import Widget from "../pages/Widget.vue";
import ClientLayout from "../layouts/ClientLayout.vue";
import CashierLayout from "../layouts/CashierLayout.vue";
import AdminLayout from "../layouts/AdminLayout.vue";
import ClientLogin from "../pages/client/Login.vue";
import ClientRegister from "../pages/client/Register.vue";
import ClientCabinet from "../pages/client/Cabinet.vue";
import ClientQR from "../pages/client/QR.vue";
import ClientOffers from "../pages/client/Offers.vue";
import ClientHistory from "../pages/client/History.vue";
import ClientProfile from "../pages/client/Profile.vue";
import CashierLogin from "../pages/cashier/Login.vue";
import CashierScan from "../pages/cashier/Scan.vue";
import CashierOperations from "../pages/cashier/Operations.vue";
import AdminLogin from "../pages/admin/Login.vue";
import AdminDashboard from "../pages/admin/Dashboard.vue";
import AdminCustomers from "../pages/admin/Customers.vue";
import AdminStaff from "../pages/admin/Staff.vue";
import AdminLocations from "../pages/admin/Locations.vue";
import AdminRules from "../pages/admin/Rules.vue";
import AdminOperations from "../pages/admin/Operations.vue";
import AdminOffers from "../pages/admin/Offers.vue";
import AdminSettings from "../pages/admin/Settings.vue";
import { useAuthStore } from "../stores/auth";

let authLoaded = false;

function getTenant(to: RouteLocationNormalized, fallback = "demo") {
  const paramTenant = Array.isArray(to.params.tenant) ? to.params.tenant[0] : to.params.tenant;
  return (paramTenant as string) || fallback;
}

function getSectionLoginPath(to: RouteLocationNormalized, tenant: string) {
  if (to.path.includes("/cashier")) {
    return `/t/${tenant}/cashier/login`;
  }
  if (to.path.includes("/admin")) {
    return `/t/${tenant}/admin/login`;
  }
  return `/t/${tenant}/login`;
}

function getSectionDefaultPath(to: RouteLocationNormalized, tenant: string) {
  if (to.path.includes("/cashier")) {
    return `/t/${tenant}/cashier/scan`;
  }
  if (to.path.includes("/admin")) {
    return `/t/${tenant}/admin/dashboard`;
  }
  return `/t/${tenant}/cabinet`;
}

function getTenantForRedirect(to: RouteLocationNormalized) {
  const auth = useAuthStore();
  if (!authLoaded) {
    auth.load();
    authLoaded = true;
  }
  return getTenant(to, auth.tenant || "demo");
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Home },
    { path: "/login", redirect: (to) => `/t/${getTenantForRedirect(to)}/login` },
    { path: "/register", redirect: (to) => `/t/${getTenantForRedirect(to)}/register` },
    { path: "/cabinet", redirect: (to) => `/t/${getTenantForRedirect(to)}/cabinet` },
    { path: "/offers", redirect: (to) => `/t/${getTenantForRedirect(to)}/offers` },
    { path: "/history", redirect: (to) => `/t/${getTenantForRedirect(to)}/history` },
    { path: "/profile", redirect: (to) => `/t/${getTenantForRedirect(to)}/profile` },
    { path: "/qr", redirect: (to) => `/t/${getTenantForRedirect(to)}/qr` },
    {
      path: "/t/:tenant",
      redirect: (to) => {
        const tenant = getTenantForRedirect(to);
        const auth = useAuthStore();
        return auth.tokens?.access ? `/t/${tenant}/cabinet` : `/t/${tenant}/login`;
      },
    },
    {
      path: "/t/:tenant",
      component: ClientLayout,
      children: [
        { path: "login", component: ClientLogin, meta: { guestOnly: true } },
        { path: "register", component: ClientRegister, meta: { guestOnly: true } },
        { path: "cabinet", component: ClientCabinet, meta: { requiresAuth: true } },
        { path: "qr", component: ClientQR, meta: { requiresAuth: true } },
        { path: "offers", component: ClientOffers, meta: { requiresAuth: true } },
        { path: "history", component: ClientHistory, meta: { requiresAuth: true } },
        { path: "profile", component: ClientProfile, meta: { requiresAuth: true } },
      ],
    },
    {
      path: "/t/:tenant/cashier",
      component: CashierLayout,
      children: [
        { path: "login", component: CashierLogin, meta: { guestOnly: true } },
        { path: "scan", component: CashierScan, meta: { requiresAuth: true } },
        { path: "operations", component: CashierOperations, meta: { requiresAuth: true } },
      ],
    },
    {
      path: "/t/:tenant/admin",
      component: AdminLayout,
      children: [
        { path: "login", component: AdminLogin, meta: { guestOnly: true } },
        { path: "dashboard", component: AdminDashboard, meta: { requiresAuth: true } },
        { path: "customers", component: AdminCustomers, meta: { requiresAuth: true } },
        { path: "staff", component: AdminStaff, meta: { requiresAuth: true } },
        { path: "locations", component: AdminLocations, meta: { requiresAuth: true } },
        { path: "rules", component: AdminRules, meta: { requiresAuth: true } },
        { path: "operations", component: AdminOperations, meta: { requiresAuth: true } },
        { path: "offers", component: AdminOffers, meta: { requiresAuth: true } },
        { path: "settings", component: AdminSettings, meta: { requiresAuth: true } },
      ],
    },
    { path: "/t/:tenant/widget", component: Widget },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!authLoaded) {
    auth.load();
    authLoaded = true;
  }

  const tenant = getTenant(to, auth.tenant || "demo");
  const hasToken = Boolean(auth.tokens?.access);

  if (to.path === "/") {
    return hasToken ? `/t/${tenant}/cabinet` : `/t/${tenant}/login`;
  }

  if (to.meta.requiresAuth && !hasToken) {
    return getSectionLoginPath(to, tenant);
  }

  if (to.meta.guestOnly && hasToken) {
    return getSectionDefaultPath(to, tenant);
  }

  return true;
});

export default router;
