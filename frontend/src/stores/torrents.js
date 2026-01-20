import { defineStore } from 'pinia'
import { torrentsApi } from '@/api'

export const useTorrentsStore = defineStore('torrents', {
  state: () => ({
    torrents: [],
    total: 0,
    page: 1,
    perPage: 50,
    pages: 0,
    categories: [],
    states: [],
    loading: false,
    error: null,
  }),

  actions: {
    async fetch(params = {}) {
      this.loading = true
      try {
        const response = await torrentsApi.list({
          page: this.page,
          per_page: this.perPage,
          ...params,
        })
        this.torrents = response.data.items
        this.total = response.data.total
        this.pages = response.data.pages
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async fetchCategories() {
      try {
        const response = await torrentsApi.categories()
        this.categories = response.data.categories
      } catch (error) {
        this.error = error.message
      }
    },

    async fetchStates() {
      try {
        const response = await torrentsApi.states()
        this.states = response.data.states
      } catch (error) {
        this.error = error.message
      }
    },

    async protect(hash, protected_) {
      const response = await torrentsApi.protect(hash, protected_)
      const index = this.torrents.findIndex(t => t.hash === hash)
      if (index !== -1) {
        this.torrents[index] = response.data
      }
      return response.data
    },

    async delete(hash, deleteFiles = true) {
      await torrentsApi.delete(hash, deleteFiles)
      this.torrents = this.torrents.filter(t => t.hash !== hash)
      this.total--
    },

    async getHistory(hash) {
      const response = await torrentsApi.history(hash)
      return response.data
    },

    async refresh() {
      const response = await torrentsApi.refresh()
      return response.data
    },

    setPage(page) {
      this.page = page
    },

    setPerPage(perPage) {
      this.perPage = perPage
      this.page = 1
    },
  },
})
