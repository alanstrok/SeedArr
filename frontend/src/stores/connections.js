import { defineStore } from 'pinia'
import { connectionsApi } from '@/api'

export const useConnectionsStore = defineStore('connections', {
  state: () => ({
    connections: [],
    loading: false,
    error: null,
  }),

  getters: {
    qbittorrentConnections: (state) => state.connections.filter(c => c.type === 'qbittorrent'),
    arrConnections: (state) => state.connections.filter(c => ['sonarr', 'radarr', 'prowlarr'].includes(c.type)),
    notificationConnections: (state) => state.connections.filter(c => ['discord', 'telegram'].includes(c.type)),
  },

  actions: {
    async fetch() {
      this.loading = true
      try {
        const response = await connectionsApi.list()
        this.connections = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async create(data) {
      const response = await connectionsApi.create(data)
      this.connections.push(response.data)
      return response.data
    },

    async update(id, data) {
      const response = await connectionsApi.update(id, data)
      const index = this.connections.findIndex(c => c.id === id)
      if (index !== -1) {
        this.connections[index] = response.data
      }
      return response.data
    },

    async delete(id) {
      await connectionsApi.delete(id)
      this.connections = this.connections.filter(c => c.id !== id)
    },

    async test(id) {
      const response = await connectionsApi.test(id)
      return response.data
    },
  },
})
