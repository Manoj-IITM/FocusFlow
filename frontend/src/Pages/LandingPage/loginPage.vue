<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import { apiUrl } from "../../api.js";
import { startAuthenticatedSession } from "../../session.js";

const router = useRouter();

const identifier = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

const handleLogin = async () => {
  error.value = "";
  loading.value = true;
  try {
    const res = await axios.post(apiUrl("/auth/login"), {
      username: identifier.value,
      password: password.value,
    });
    if (res.data && res.data.user) {
      startAuthenticatedSession(res.data.user);
      router.push("/dashboard");
    } else {
      error.value = "Sign in could not be completed. Please try again.";
    }
  } catch (err) {
    if (err.response) {
      error.value = err.response.data?.error || "Unable to sign in. Please check your details and try again.";
    } else {
      error.value = "FocusFlow is unavailable right now. Check your connection and try again.";
    }
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="auth-page">
    <!-- Ambient glowing backdrop effect -->
    <div class="glow-orb orb-1"></div>
    <div class="glow-orb orb-2"></div>

    <div class="auth-card">
      <div class="brand-header">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12c0-2.25.744-4.327 2-6l8 6z" />
            <path d="M12 2c2.5 3.5 3 7 1 10" />
          </svg>
        </div>
        <h1 class="brand-title">FocusFlow</h1>
        <p class="brand-subtitle">Your focus today builds your tomorrow.</p>
      </div>

      <div class="form-wrapper">
        <h2 class="form-heading">Welcome Back</h2>
        <p class="form-desc">Enter your credentials to access your study environment.</p>

        <div v-if="error" class="error-badge">
          <i class="ti ti-alert-circle"></i>
          <span>{{ error }}</span>
        </div>

        <form @submit.prevent="handleLogin" class="auth-form">
          <div class="input-group">
            <label>Username or Email</label>
            <div class="input-wrap">
              <i class="ti ti-user input-icon"></i>
              <input
                type="text"
                v-model="identifier"
                placeholder="e.g. Alex or alex@focusflow.app"
                required
              />
            </div>
          </div>

          <div class="input-group">
            <div class="label-row">
              <label>Password</label>
              <a href="#" class="forgot-link">Forgot password?</a>
            </div>
            <div class="input-wrap">
              <i class="ti ti-lock input-icon"></i>
              <input
                type="password"
                v-model="password"
                placeholder="Enter password"
                required
              />
            </div>
          </div>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="loading">Signing In...</span>
            <span v-else>Sign In to Workspace</span>
            <i class="ti ti-arrow-right"></i>
          </button>
        </form>

        <div class="switch-auth">
          <span>Don't have an account?</span>
          <router-link to="/signup" class="switch-link">Create Account</router-link>
        </div>
        <router-link to="/" class="home-link">Back to homepage</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: #080811;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #f1f5f9;
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
  opacity: 0.22;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #38bdf8, #6366f1);
  top: -100px;
  left: -100px;
}

.orb-2 {
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, #2dd4bf, #0284c7);
  bottom: -80px;
  right: -80px;
}

.auth-card {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 440px;
  background: rgba(14, 17, 30, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 30px rgba(56, 189, 248, 0.05);
}

.brand-header {
  text-align: center;
  margin-bottom: 32px;
}

.brand-logo {
  width: 52px;
  height: 52px;
  margin: 0 auto 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(45, 212, 191, 0.18), rgba(56, 189, 248, 0.1));
  border: 1px solid rgba(45, 212, 191, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2dd4bf;
}

.brand-logo svg {
  width: 28px;
  height: 28px;
}

.brand-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #ffffff;
  margin: 0;
}

.brand-subtitle {
  font-size: 13px;
  color: #94a3b8;
  margin: 6px 0 0;
}

.form-heading {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 6px;
}

.form-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 24px;
  line-height: 1.5;
}

.error-badge {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: #f87171;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
}

.label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forgot-link {
  font-size: 12px;
  color: #2dd4bf;
  text-decoration: none;
  transition: opacity 0.2s;
}

.forgot-link:hover {
  opacity: 0.8;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 14px;
  color: #64748b;
  font-size: 18px;
}

.input-wrap input {
  width: 100%;
  background: rgba(8, 10, 18, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 12px;
  padding: 12px 14px 12px 42px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.input-wrap input:focus {
  border-color: #2dd4bf;
  box-shadow: 0 0 0 3px rgba(45, 212, 191, 0.15);
  background: rgba(12, 15, 26, 0.9);
}

.input-wrap input::placeholder {
  color: #475569;
}

.submit-btn {
  margin-top: 8px;
  background: linear-gradient(135deg, #14b8a6, #0284c7);
  border: none;
  border-radius: 12px;
  padding: 14px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.25s ease;
  box-shadow: 0 8px 20px -4px rgba(20, 184, 166, 0.35);
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.95;
  transform: translateY(-1px);
  box-shadow: 0 10px 25px -4px rgba(20, 184, 166, 0.45);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.quick-demo-box {
  margin-top: 18px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  text-align: center;
}

.demo-hint {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

.switch-auth {
  margin-top: 24px;
  text-align: center;
  font-size: 13px;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.switch-link {
  color: #2dd4bf;
  text-decoration: none;
  font-weight: 500;
}

.switch-link:hover {
  text-decoration: underline;
}

.home-link {
  display: block;
  margin-top: 14px;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
  text-decoration: none;
}

.home-link:hover {
  color: #5eead4;
}
</style>
