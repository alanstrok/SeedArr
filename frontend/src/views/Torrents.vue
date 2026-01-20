<template>
  <div>
    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" sm="4" md="3">
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search"
              density="compact"
              hide-details
              clearable
              @update:model-value="debouncedFetch"
            ></v-text-field>
          </v-col>
          <v-col cols="12" sm="4" md="2">
            <v-select
              v-model="filterTracker"
              :items="trackerOptions"
              label="Tracker"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchTorrents"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="4" md="2">
            <v-select
              v-model="filterCategory"
              :items="categoryOptions"
              label="Category"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchTorrents"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="4" md="2">
            <v-select
              v-model="filterState"
              :items="stateOptions"
              label="State"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchTorrents"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="4" md="2">
            <v-select
              v-model="filterProtected"
              :items="protectedOptions"
              label="Protected"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchTorrents"
            ></v-select>
          </v-col>
          <v-col cols="auto">
            <v-btn icon @click="refreshTorrents" :loading="refreshing">
              <v-icon>mdi-sync</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Torrents Table -->
    <v-card>
      <v-data-table-server
        v-model:items-per-page="perPage"
        v-model:page="page"
        :headers="headers"
        :items="torrents"
        :items-length="total"
        :loading="loading"
        :items-per-page-options="[25, 50, 100]"
        @update:options="onTableOptions"
      >
        <template v-slot:item.name="{ item }">
          <div class="text-truncate" style="max-width: 300px;">
            <v-tooltip :text="item.name" location="top">
              <template v-slot:activator="{ props }">
                <span v-bind="props">{{ item.name }}</span>
              </template>
            </v-tooltip>
          </div>
        </template>

        <template v-slot:item.tracker_name="{ item }">
          <v-chip v-if="item.tracker_name" size="small" label>
            {{ item.tracker_name }}
          </v-chip>
          <span v-else class="text-medium-emphasis">-</span>
        </template>

        <template v-slot:item.size_bytes="{ item }">
          {{ formatBytes(item.size_bytes) }}
        </template>

        <template v-slot:item.ratio="{ item }">
          <v-chip
            :color="getRatioColor(item.ratio)"
            size="small"
            label
          >
            {{ item.ratio.toFixed(2) }}
          </v-chip>
        </template>

        <template v-slot:item.seed_time_seconds="{ item }">
          {{ formatSeedTime(item.seed_time_seconds) }}
        </template>

        <template v-slot:item.state="{ item }">
          <v-chip
            :color="getStateColor(item.state)"
            size="small"
            label
          >
            {{ item.state }}
          </v-chip>
        </template>

        <template v-slot:item.protected="{ item }">
          <v-icon
            v-if="item.protected"
            color="success"
            size="small"
          >mdi-shield-check</v-icon>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon
            size="small"
            variant="text"
            @click="showDetails(item)"
          >
            <v-icon>mdi-eye</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            @click="toggleProtect(item)"
          >
            <v-icon>{{ item.protected ? 'mdi-shield-off' : 'mdi-shield-plus' }}</v-icon>
          </v-btn>
          <v-btn
            icon
            size="small"
            variant="text"
            color="error"
            @click="confirmDelete(item)"
          >
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800">
      <v-card v-if="selectedTorrent">
        <v-card-title>{{ selectedTorrent.name }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Hash</v-list-item-title>
                  <v-list-item-subtitle class="text-truncate">{{ selectedTorrent.hash }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Tracker</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTorrent.tracker_name || '-' }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Category</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTorrent.category || '-' }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Size</v-list-item-title>
                  <v-list-item-subtitle>{{ formatBytes(selectedTorrent.size_bytes) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Ratio</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTorrent.ratio.toFixed(3) }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
            <v-col cols="12" md="6">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Seed Time</v-list-item-title>
                  <v-list-item-subtitle>{{ formatSeedTime(selectedTorrent.seed_time_seconds) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Uploaded</v-list-item-title>
                  <v-list-item-subtitle>{{ formatBytes(selectedTorrent.uploaded_bytes) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Seeds / Leeches</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTorrent.num_seeds }} / {{ selectedTorrent.num_leeches }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Added On</v-list-item-title>
                  <v-list-item-subtitle>{{ formatDate(selectedTorrent.added_on) }}</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>State</v-list-item-title>
                  <v-list-item-subtitle>{{ selectedTorrent.state }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>

          <v-divider class="my-4"></v-divider>

          <h4 class="mb-2">Action History</h4>
          <v-data-table
            :headers="historyHeaders"
            :items="torrentHistory"
            :loading="historyLoading"
            density="compact"
            :items-per-page="5"
          >
            <template v-slot:item.created_at="{ item }">
              {{ formatDate(item.created_at) }}
            </template>
            <template v-slot:item.action="{ item }">
              <v-chip :color="getActionColor(item.action)" size="small" label>
                {{ item.action }}
              </v-chip>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="detailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Torrent</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ torrentToDelete?.name }}"?
          <v-checkbox
            v-model="deleteFiles"
            label="Also delete files"
            color="error"
            class="mt-2"
          ></v-checkbox>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteTorrent" :loading="deleting">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject } from 'vue'
import { useTorrentsStore } from '@/stores/torrents'
import { useTrackersStore } from '@/stores/trackers'
import { torrentsApi } from '@/api'
import { format } from 'date-fns'

const showSnackbar = inject('showSnackbar')
const torrentsStore = useTorrentsStore()
const trackersStore = useTrackersStore()

const loading = ref(false)
const refreshing = ref(false)
const torrents = ref([])
const total = ref(0)
const page = ref(1)
const perPage = ref(50)

const search = ref('')
const filterTracker = ref(null)
const filterCategory = ref(null)
const filterState = ref(null)
const filterProtected = ref(null)

const categoryOptions = ref([])
const stateOptions = ref([])
const trackerOptions = ref([])

const detailsDialog = ref(false)
const selectedTorrent = ref(null)
const torrentHistory = ref([])
const historyLoading = ref(false)

const deleteDialog = ref(false)
const torrentToDelete = ref(null)
const deleteFiles = ref(true)
const deleting = ref(false)

const protectedOptions = [
  { title: 'Protected', value: true },
  { title: 'Not Protected', value: false },
]

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Tracker', key: 'tracker_name', width: '120px' },
  { title: 'Size', key: 'size_bytes', width: '100px' },
  { title: 'Ratio', key: 'ratio', width: '80px' },
  { title: 'Seed Time', key: 'seed_time_seconds', width: '100px' },
  { title: 'State', key: 'state', width: '100px' },
  { title: '', key: 'protected', width: '40px' },
  { title: 'Actions', key: 'actions', width: '140px', sortable: false },
]

const historyHeaders = [
  { title: 'Date', key: 'created_at', width: '150px' },
  { title: 'Action', key: 'action', width: '100px' },
  { title: 'Rule', key: 'rule_name' },
  { title: 'Reason', key: 'reason' },
]

let debounceTimer = null
const debouncedFetch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchTorrents, 300)
}

const fetchTorrents = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
    }
    if (search.value) params.search = search.value
    if (filterTracker.value) params.tracker_id = filterTracker.value
    if (filterCategory.value) params.category = filterCategory.value
    if (filterState.value) params.state = filterState.value
    if (filterProtected.value !== null) params.protected = filterProtected.value

    const response = await torrentsApi.list(params)
    torrents.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    showSnackbar('Failed to load torrents', 'error')
  } finally {
    loading.value = false
  }
}

const loadFilters = async () => {
  try {
    const [categoriesRes, statesRes] = await Promise.all([
      torrentsApi.categories(),
      torrentsApi.states(),
    ])
    categoryOptions.value = categoriesRes.data.categories
    stateOptions.value = statesRes.data.states

    await trackersStore.fetch()
    trackerOptions.value = trackersStore.trackers.map(t => ({
      title: t.name,
      value: t.id,
    }))
  } catch (error) {
    console.error('Failed to load filters:', error)
  }
}

const refreshTorrents = async () => {
  refreshing.value = true
  try {
    await torrentsApi.refresh()
    await fetchTorrents()
    showSnackbar('Torrents refreshed', 'success')
  } catch (error) {
    showSnackbar('Failed to refresh torrents', 'error')
  } finally {
    refreshing.value = false
  }
}

const onTableOptions = ({ page: p, itemsPerPage }) => {
  page.value = p
  perPage.value = itemsPerPage
  fetchTorrents()
}

const showDetails = async (torrent) => {
  selectedTorrent.value = torrent
  detailsDialog.value = true
  historyLoading.value = true
  try {
    const response = await torrentsApi.history(torrent.hash)
    torrentHistory.value = response.data
  } catch (error) {
    console.error('Failed to load history:', error)
  } finally {
    historyLoading.value = false
  }
}

const toggleProtect = async (torrent) => {
  try {
    await torrentsApi.protect(torrent.hash, !torrent.protected)
    torrent.protected = !torrent.protected
    showSnackbar(`Torrent ${torrent.protected ? 'protected' : 'unprotected'}`, 'success')
  } catch (error) {
    showSnackbar('Failed to update protection', 'error')
  }
}

const confirmDelete = (torrent) => {
  torrentToDelete.value = torrent
  deleteFiles.value = true
  deleteDialog.value = true
}

const deleteTorrent = async () => {
  deleting.value = true
  try {
    await torrentsApi.delete(torrentToDelete.value.hash, deleteFiles.value)
    torrents.value = torrents.value.filter(t => t.hash !== torrentToDelete.value.hash)
    total.value--
    deleteDialog.value = false
    showSnackbar('Torrent deleted', 'success')
  } catch (error) {
    showSnackbar('Failed to delete torrent', 'error')
  } finally {
    deleting.value = false
  }
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatSeedTime = (seconds) => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  if (days > 0) return `${days}d ${hours}h`
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

const formatDate = (date) => {
  if (!date) return ''
  return format(new Date(date), 'MMM d, yyyy HH:mm')
}

const getRatioColor = (ratio) => {
  if (ratio >= 2) return 'success'
  if (ratio >= 1) return 'info'
  if (ratio >= 0.5) return 'warning'
  return 'error'
}

const getStateColor = (state) => {
  if (['uploading', 'stalledUP', 'forcedUP'].includes(state)) return 'success'
  if (['downloading', 'stalledDL'].includes(state)) return 'info'
  if (state.includes('paused')) return 'warning'
  return 'grey'
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

const handleRefresh = () => {
  fetchTorrents()
}

onMounted(() => {
  loadFilters()
  fetchTorrents()
  window.addEventListener('refresh-data', handleRefresh)
})

onUnmounted(() => {
  window.removeEventListener('refresh-data', handleRefresh)
})
</script>
