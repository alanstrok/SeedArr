<template>
  <v-app>
    <!-- Navigation Drawer -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail"
      permanent
      @click="rail = false"
    >
      <v-list-item
        prepend-icon="mdi-seed"
        title="SeedArr"
        subtitle="v1.0.0"
        nav
      >
        <template v-slot:append>
          <v-btn
            variant="text"
            :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
            @click.stop="rail = !rail"
          ></v-btn>
        </template>
      </v-list-item>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          v-for="route in routes"
          :key="route.name"
          :to="route.path"
          :prepend-icon="route.meta.icon"
          :title="route.meta.title"
          :active="$route.name === route.name"
          color="primary"
        ></v-list-item>
      </v-list>

      <template v-slot:append>
        <v-divider></v-divider>
        <v-list density="compact" nav>
          <v-list-item
            prepend-icon="mdi-play-circle"
            title="Run Scan"
            @click="runScan(false)"
            :disabled="scanning"
          >
            <template v-slot:append v-if="scanning">
              <v-progress-circular
                indeterminate
                size="20"
                width="2"
              ></v-progress-circular>
            </template>
          </v-list-item>
          <v-list-item
            prepend-icon="mdi-play-circle-outline"
            title="Dry Run"
            @click="runScan(true)"
            :disabled="scanning"
          ></v-list-item>
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- App Bar -->
    <v-app-bar density="compact" flat>
      <v-app-bar-title>{{ $route.meta.title }}</v-app-bar-title>

      <template v-slot:append>
        <v-btn icon @click="refreshData">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
        <v-btn icon @click="toggleTheme">
          <v-icon>{{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
        </v-btn>
      </template>
    </v-app-bar>

    <!-- Main Content -->
    <v-main>
      <v-container fluid class="pa-4">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
      location="bottom right"
    >
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, provide, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import api from '@/api'

const router = useRouter()
const theme = useTheme()

const drawer = ref(true)
const rail = ref(false)
const scanning = ref(false)

const routes = router.getRoutes().filter(r => r.meta?.title)

const isDark = computed(() => theme.global.current.value.dark)

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

// Snackbar state
const snackbar = reactive({
  show: false,
  text: '',
  color: 'success',
  timeout: 3000,
})

const showSnackbar = (text, color = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// Provide snackbar to all components
provide('showSnackbar', showSnackbar)

const runScan = async (dryRun) => {
  scanning.value = true
  try {
    const endpoint = dryRun ? '/api/scan/dry-run' : '/api/scan'
    const response = await api.post(endpoint)
    const result = response.data
    const message = dryRun
      ? `Dry run complete: ${result.actions_taken} actions would be taken`
      : `Scan complete: ${result.actions_taken} actions taken`
    showSnackbar(message, 'success')
  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Scan failed', 'error')
  } finally {
    scanning.value = false
  }
}

const refreshData = () => {
  // Emit refresh event to current view
  window.dispatchEvent(new CustomEvent('refresh-data'))
}
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
