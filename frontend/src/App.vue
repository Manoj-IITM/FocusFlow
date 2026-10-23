<script setup>
import ThemeSwitcher from "./components/ThemeSwitcher.vue";
</script>

<template>
  <div class="app-shell">
    <router-view v-slot="{ Component, route }">
      <KeepAlive>
        <component :is="Component" v-if="route.name === 'dashboard'" />
      </KeepAlive>
      <component :is="Component" v-if="route.name !== 'dashboard'" />
      <ThemeSwitcher v-if="route.name !== 'dashboard'" />
    </router-view>
  </div>
</template>

<style>
body {
  background: #080811;
  color: #f5f5f7;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 0;
}
</style>
