import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../session.js";

import LandingPage from "../Pages/LandingPage/landingPage.vue";
import LoginPage from "../Pages/LandingPage/loginPage.vue";
import SignupPage from "../Pages/LandingPage/signupPage.vue";
import DashboardPage from "../Pages/Dashboard/dashboardPage.vue";
import DashboardSectionPage from "../Pages/Dashboard/dashboardSectionPage.vue";

const routes = [
  { path: "/", name: "landing", component: LandingPage },
  { path: "/login", name: "login", component: LoginPage, meta: { requiresGuest: true } },
  { path: "/signup", name: "signup", component: SignupPage, meta: { requiresGuest: true } },
  { path: "/dashboard", name: "dashboard", component: DashboardPage, meta: { requiresAuth: true } },
  {
    path: "/analyse",
    name: "analyse",
    component: DashboardSectionPage,
    meta: { title: "Analyse", icon: "ti ti-chart-bar", requiresAuth: true },
  },
  {
    path: "/profile",
    name: "profile",
    component: DashboardSectionPage,
    meta: { title: "Profile", icon: "ti ti-user", requiresAuth: true },
  },
  {
    path: "/settings",
    name: "settings",
    component: DashboardSectionPage,
    meta: { title: "Settings", icon: "ti ti-settings", requiresAuth: true },
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  // createWebHistory gives clean URLs like /login instead of /#/login
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  // Offline demo sessions are allowed to browse protected routes as well;
  // only the API calls made from those pages require a real access token.
  const authenticated = isAuthenticated();
  if (to.meta.requiresAuth && !authenticated) {
    return { name: "login" };
  }
  if (to.meta.requiresGuest && authenticated) {
    return { name: "dashboard" };
  }
});

export default router;
