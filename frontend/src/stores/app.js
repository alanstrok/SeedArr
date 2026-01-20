import { defineStore } from 'pinia'
import { systemApi } from '@/api'

export const useAppStore = defineStore('app', {
  state: () => ({
    stats: null,
    settings: null,
    health: null,
    loading: false,
    error: null,
  }),

  actions: {
    async fetchStats() {
      this.loading = true
      try {
        const response = await systemApi.stats()
        this.stats = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async fetchSettings() {
      try {
        const response = await systemApi.settings()
        this.settings = response.data
      } catch (error) {
        this.error = error.message
      }
    },

    async updateSettings(data) {
      try {
        const response = await systemApi.updateSettings(data)
        this.settings = response.data
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchHealth() {
      try {
        const response = await systemApi.health()
        this.health = response.data
      } catch (error) {
        this.error = error.message
      }
    },
  },
})
