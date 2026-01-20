<template>
  <div>
    <!-- Zone Distribution Card -->
    <v-card class="mb-4">
      <v-card-text>
        <div class="d-flex justify-space-around align-center text-center">
          <div>
            <div class="text-h3 text-error">{{ zoneSummary?.total_zone1 || 0 }}</div>
            <div class="text-subtitle-2">Zone 1</div>
            <div class="text-caption text-medium-emphasis">Obligations</div>
          </div>
          <v-divider vertical class="mx-4"></v-divider>
          <div>
            <div class="text-h3 text-warning">{{ zoneSummary?.total_zone2 || 0 }}</div>
            <div class="text-subtitle-2">Zone 2</div>
            <div class="text-caption text-medium-emphasis">Preferences</div>
          </div>
          <v-divider vertical class="mx-4"></v-divider>
          <div>
            <div class="text-h3 text-success">{{ zoneSummary?.total_zone3 || 0 }}</div>
            <div class="text-subtitle-2">Zone 3</div>
            <div class="text-caption text-medium-emphasis">Eligible</div>
          </div>
          <v-divider vertical class="mx-4"></v-divider>
          <div>
            <div class="text-h3">{{ stats?.total_torrents || 0 }}</div>
            <div class="text-subtitle-2">Total</div>
            <div class="text-caption text-medium-emphasis">Torrents</div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Stats Cards -->
    <v-row>
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
            <v-avatar color="teal" class="mr-4">
              <v-icon>mdi-upload</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5">{{ formatBytes(stats?.total_upload_bytes || 0) }}</div>
              <div class="text-caption text-medium-emphasis">Total Upload</div>
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

    <!-- Second Row - Disk Space & Protected -->
    <v-row class="mt-2">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar :color="diskSpaceColor" class="mr-4">
              <v-icon>mdi-database</v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ diskSpacePercent }}%</div>
              <div class="text-caption text-medium-emphasis">Disk Free</div>
            </div>
          </v-card-text>
          <v-progress-linear
            :model-value="100 - diskSpacePercent"
            :color="diskSpaceColor"
            height="4"
          ></v-progress-linear>
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
              <div class="text-caption text-medium-emphasis">Active Seeding</div>
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
              <v-icon>mdi-server-network</v-icon>
            </v-avatar>
            <div>
              <div class="text-h6">{{ stats?.trackers_count || 0 }}</div>
              <div class="text-caption text-medium-emphasis">Trackers</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Main Content Row -->
    <v-row class="mt-4">
      <!-- Zone Distribution by Tracker -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-chart-donut</v-icon>
            Zone Distribution
          </v-card-title>
          <v-card-text v-if="zoneSummary?.trackers?.length">
            <v-list density="compact">
              <v-list-item v-for="tracker in zoneSummary.trackers.slice(0, 6)" :key="tracker.id">
                <v-list-item-title class="d-flex align-center justify-space-between">
                  <span class="text-truncate" style="max-width: 120px;">{{ tracker.name }}</span>
                  <div>
                    <v-chip size="x-small" color="error" variant="flat" class="mx-1">{{ tracker.zone1 }}</v-chip>
                    <v-chip size="x-small" color="warning" variant="flat" class="mx-1">{{ tracker.zone2 }}</v-chip>
                    <v-chip size="x-small" color="success" variant="flat" class="mx-1">{{ tracker.zone3 }}</v-chip>
                  </div>
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-text v-else class="text-center text-grey">
            No trackers configured
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn variant="text" to="/trackers">Manage Trackers</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <!-- Recent Actions -->
      <v-col cols="12" md="5">
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

      <!-- System Status -->
      <v-col cols="12" md="3">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-heart-pulse</v-icon>
            System
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="health?.database === 'connected' ? 'success' : 'error'" size="small">
                    mdi-database
                  </v-icon>
                </template>
                <v-list-item-title>Database</v-list-item-title>
                <v-list-item-subtitle>{{ health?.database || 'Unknown' }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="health?.qbittorrent === 'connected' ? 'success' : health?.qbittorrent ? 'error' : 'grey'" size="small">
                    mdi-download-box
                  </v-icon>
                </template>
                <v-list-item-title>qBittorrent</v-list-item-title>
                <v-list-item-subtitle>{{ health?.qbittorrent || 'Not configured' }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template v-slot:prepend>
                  <v-icon :color="health?.scheduler === 'running' ? 'success' : 'error'" size="small">
                    mdi-clock
                  </v-icon>
                </template>
                <v-list-item-title>Scheduler</v-list-item-title>
                <v-list-item-subtitle>{{ health?.scheduler || 'Unknown' }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="stats?.last_scan">
                <template v-slot:prepend>
                  <v-icon color="info" size="small">mdi-radar</v-icon>
                </template>
                <v-list-item-title>Last Scan</v-list-item-title>
                <v-list-item-subtitle>{{ formatDate(stats.last_scan) }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <!-- Quick Actions -->
        <v-card class="mt-4">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-lightning-bolt</v-icon>
            Quick Actions
          </v-card-title>
          <v-card-text>
            <v-btn
              block
              color="primary"
              variant="outlined"
              @click="runScan"
              :loading="scanning"
              class="mb-2"
            >
              <v-icon start>mdi-radar</v-icon>
              Run Zone Scan
            </v-btn>
            <v-btn
              block
              variant="outlined"
              to="/torrents"
            >
              <v-icon start>mdi-view-list</v-icon>
              View Torrents
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { systemApi, trackersApi } from '@/api'
import { format } from 'date-fns'

const showSnackbar = inject('showSnackbar')

const stats = ref(null)
const health = ref(null)
const zoneSummary = ref(null)
const recentLogs = ref([])
const logsLoading = ref(false)
const scanning = ref(false)

const logHeaders = [
  { title: 'Date', key: 'created_at', width: '100px' },
  { title: 'Torrent', key: 'torrent_name' },
  { title: 'Action', key: 'action', width: '80px' },
  { title: '', key: 'dry_run', width: '30px' },
]

const diskSpacePercent = computed(() => {
  if (!stats.value?.disk_free_percent) return 50
  return Math.round(stats.value.disk_free_percent)
})

const diskSpaceColor = computed(() => {
  const percent = diskSpacePercent.value
  if (percent < 10) return 'error'
  if (percent < 20) return 'warning'
  return 'success'
})

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
    case 'zone_updated': return 'primary'
    default: return 'grey'
  }
}

const loadData = async () => {
  try {
    const [statsRes, healthRes, logsRes, zoneRes] = await Promise.all([
      systemApi.stats(),
      systemApi.health(),
      systemApi.logs({ per_page: 5 }),
      trackersApi.zoneSummary(),
    ])
    stats.value = statsRes.data
    health.value = healthRes.data
    recentLogs.value = logsRes.data.items
    zoneSummary.value = zoneRes.data
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

const runScan = async () => {
  scanning.value = true
  try {
    await systemApi.scan(false)
    showSnackbar('Scan completed', 'success')
    await loadData()
  } catch (error) {
    showSnackbar('Scan failed', 'error')
  } finally {
    scanning.value = false
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
