<template>
  <div>
    <!-- Stats Cards -->
    <v-row>
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="primary" class="mr-4">
              <v-icon>mdi-download</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5">{{ stats?.total_torrents || 0 }}</div>
              <div class="text-caption text-medium-emphasis">Total Torrents</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="success" class="mr-4">
              <v-icon>mdi-swap-vertical</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5">{{ stats?.average_ratio?.toFixed(2) || '0.00' }}</div>
              <div class="text-caption text-medium-emphasis">Average Ratio</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="info" class="mr-4">
              <v-icon>mdi-harddisk</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5">{{ formatBytes(stats?.total_size_bytes || 0) }}</div>
              <div class="text-caption text-medium-emphasis">Total Size</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="warning" class="mr-4">
              <v-icon>mdi-lightning-bolt</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5">{{ stats?.actions_today || 0 }}</div>
              <div class="text-caption text-medium-emphasis">Actions Today</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Second Row Stats -->
    <v-row class="mt-2">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="teal" class="mr-4">
              <v-icon>mdi-upload</v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ formatBytes(stats?.total_upload_bytes || 0) }}</div>
              <div class="text-caption text-medium-emphasis">Total Uploaded</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="purple" class="mr-4">
              <v-icon>mdi-play-circle</v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ stats?.active_torrents || 0 }}</div>
              <div class="text-caption text-medium-emphasis">Active Torrents</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="orange" class="mr-4">
              <v-icon>mdi-shield-check</v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ stats?.protected_count || 0 }}</div>
              <div class="text-caption text-medium-emphasis">Protected</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar color="cyan" class="mr-4">
              <v-icon>mdi-format-list-checks</v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ stats?.rules_count || 0 }}</div>
              <div class="text-caption text-medium-emphasis">Active Rules</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Actions & Status -->
    <v-row class="mt-4">
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-history</v-icon>
            Recent Actions
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="logHeaders"
              :items="recentLogs"
              :loading="logsLoading"
              density="compact"
              :items-per-page="5"
              hide-default-footer
            >
              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>
              <template v-slot:item.action="{ item }">
                <v-chip
                  :color="getActionColor(item.action)"
                  size="small"
                  label
                >
                  {{ item.action }}
                </v-chip>
              </template>
              <template v-slot:item.dry_run="{ item }">
                <v-icon v-if="item.dry_run" color="info" size="small">mdi-test-tube</v-icon>
              </template>
            </v-data-table>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" to="/logs">View All Logs</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <v-col cols="12" md="4">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-heart-pulse</v-icon>
            System Status
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="health?.database === 'connected' ? 'success' : 'error'">
                    mdi-database
                  </v-icon>
                </template>
                <v-list-item-title>Database</v-list-item-title>
                <v-list-item-subtitle>{{ health?.database || 'Unknown' }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="health?.qbittorrent === 'connected' ? 'success' : health?.qbittorrent ? 'error' : 'grey'">
                    mdi-download-box
                  </v-icon>
                </template>
                <v-list-item-title>qBittorrent</v-list-item-title>
                <v-list-item-subtitle>{{ health?.qbittorrent || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="health?.scheduler === 'running' ? 'success' : 'error'">
                    mdi-clock
                  </v-icon>
                </template>
                <v-list-item-title>Scheduler</v-list-item-title>
                <v-list-item-subtitle>{{ health?.scheduler || 'Unknown' }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="stats?.last_scan">
                <template v-slot:prepend>
                  <v-icon color="info">mdi-radar</v-icon>
                </template>
                <v-list-item-title>Last Scan</v-list-item-title>
                <v-list-item-subtitle>{{ formatDate(stats.last_scan) }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <v-card class="mt-4">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-server-network</v-icon>
            Trackers
          </v-card-title>
          <v-card-text>
            <div class="text-h4 text-center">{{ stats?.trackers_count || 0 }}</div>
            <div class="text-caption text-center text-medium-emphasis">Configured Trackers</div>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" to="/trackers">Manage Trackers</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { systemApi } from '@/api'
import { format } from 'date-fns'

const appStore = useAppStore()

const stats = ref(null)
const health = ref(null)
const recentLogs = ref([])
const logsLoading = ref(false)

const logHeaders = [
  { title: 'Date', key: 'created_at', width: '150px' },
  { title: 'Torrent', key: 'torrent_name' },
  { title: 'Action', key: 'action', width: '100px' },
  { title: '', key: 'dry_run', width: '40px' },
]

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (date) => {
  if (!date) return ''
  return format(new Date(date), 'MMM d, HH:mm')
}

const getActionColor = (action) => {
  switch (action) {
    case 'deleted': return 'error'
    case 'paused': return 'warning'
    case 'tagged': return 'info'
    case 'protected': return 'success'
    default: return 'grey'
  }
}

const loadData = async () => {
  try {
    const [statsRes, healthRes, logsRes] = await Promise.all([
      systemApi.stats(),
      systemApi.health(),
      systemApi.logs({ per_page: 5 }),
    ])
    stats.value = statsRes.data
    health.value = healthRes.data
    recentLogs.value = logsRes.data.items
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

const handleRefresh = () => {
  loadData()
}

onMounted(() => {
  loadData()
  window.addEventListener('refresh-data', handleRefresh)
})

onUnmounted(() => {
  window.removeEventListener('refresh-data', handleRefresh)
})
</script>
