import { createApp } from "vue";
import App from "./App.vue";
import router from "./Router/router.js";
import { initializeTheme } from "./theme.js";
import { initializeCustomScrollbars } from "./scrollbars.js";
import "./theme.css";
import axios from "axios";
import { readAccessToken } from "./session.js";

axios.interceptors.request.use((config) => {
	const token = readAccessToken();
	if (token) config.headers.Authorization = `Bearer ${token}`;
	return config;
});

initializeTheme();

createApp(App)
.use(router)
.mount("#app");

initializeCustomScrollbars();
