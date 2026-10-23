import { createRouter, createWebHistory } from "vue-router";
import { isAuthenticated } from "../session.js";

import LandingPage from "../Pages/LandingPage/landingPage.vue";
import LoginPage from "../Pages/LandingPage/loginPage.vue";
import SignupPage from "../Pages/LandingPage/signupPage.vue";
import DashboardPage from "../Pages/Dashboard/dashboardPage.vue";
import AnalyzePage from "../Pages/Analyze/analyzePage.vue";

const routes = [
  { path: "/", name: "landing", component: LandingPage },
  { path: "/login", name: "login", component: LoginPage },
  { path: "/signup", name: "signup", component: SignupPage },
  { path: "/dashboard", name: "dashboard", component: DashboardPage },
  { path: "/analyze", name: "analyze", component: AnalyzePage },
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
