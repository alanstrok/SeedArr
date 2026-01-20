import { defineStore } from 'pinia'
import { rulesApi } from '@/api'

export const useRulesStore = defineStore('rules', {
  state: () => ({
    rules: [],
    loading: false,
    error: null,
  }),

  getters: {
    enabledRules: (state) => state.rules.filter(r => r.enabled),
    sortedRules: (state) => [...state.rules].sort((a, b) => a.priority - b.priority),
  },

  actions: {
    async fetch() {
      this.loading = true
      try {
        const response = await rulesApi.list()
        this.rules = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async create(data) {
      const response = await rulesApi.create(data)
      this.rules.push(response.data)
      return response.data
    },

    async update(id, data) {
      const response = await rulesApi.update(id, data)
      const index = this.rules.findIndex(r => r.id === id)
      if (index !== -1) {
        this.rules[index] = response.data
      }
      return response.data
    },

    async delete(id) {
      await rulesApi.delete(id)
      this.rules = this.rules.filter(r => r.id !== id)
    },

    async reorder(ruleIds) {
      const response = await rulesApi.reorder(ruleIds)
      this.rules = response.data
      return response.data
    },

    async test(id) {
      const response = await rulesApi.test(id)
      return response.data
    },

    async execute(id, dryRun = true) {
      const response = await rulesApi.execute(id, dryRun)
      return response.data
    },
  },
})
