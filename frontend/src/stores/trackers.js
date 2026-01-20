import { defineStore } from 'pinia'
import { trackersApi } from '@/api'

export const useTrackersStore = defineStore('trackers', {
  state: () => ({
    trackers: [],
    discovered: [],
    zoneSummary: null,
    loading: false,
    error: null,
  }),

  actions: {
    async fetch() {
      this.loading = true
      try {
        const response = await trackersApi.list()
        this.trackers = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async fetchZoneSummary() {
      try {
        const response = await trackersApi.zoneSummary()
        this.zoneSummary = response.data
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async create(data) {
      const response = await trackersApi.create(data)
      this.trackers.push(response.data)
      return response.data
    },

    async update(id, data) {
      const response = await trackersApi.update(id, data)
      const index = this.trackers.findIndex(t => t.id === id)
      if (index !== -1) {
        this.trackers[index] = response.data
      }
      return response.data
    },

    async delete(id) {
      await trackersApi.delete(id)
      this.trackers = this.trackers.filter(t => t.id !== id)
    },

    async toggle(id) {
      const response = await trackersApi.toggle(id)
      const index = this.trackers.findIndex(t => t.id === id)
      if (index !== -1) {
        this.trackers[index] = response.data
      }
      return response.data
    },

    async togglePermaseed(id) {
      const response = await trackersApi.togglePermaseed(id)
      const index = this.trackers.findIndex(t => t.id === id)
      if (index !== -1) {
        this.trackers[index] = response.data
      }
      return response.data
    },

    async discover() {
      this.loading = true
      try {
        const response = await trackersApi.discover()
        this.discovered = response.data
        return response.data
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async getStats(id) {
      const response = await trackersApi.stats(id)
      return response.data
    },

    async updateStats(id) {
      const response = await trackersApi.updateStats(id)
      const index = this.trackers.findIndex(t => t.id === id)
      if (index !== -1) {
        this.trackers[index] = response.data
      }
      return response.data
    },
  },
})
