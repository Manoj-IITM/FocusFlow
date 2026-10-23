import { createRouter, createWebHistory } from "vue-router";

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

export default router;
