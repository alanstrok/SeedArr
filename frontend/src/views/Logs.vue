<template>
  <div>
    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" sm="6" md="2">
            <v-select
              v-model="filterAction"
              :items="actionOptions"
              label="Action"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchLogs"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="2">
            <v-select
              v-model="filterTracker"
              :items="trackerOptions"
              label="Tracker"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchLogs"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="2">
            <v-select
              v-model="filterRule"
              :items="ruleOptions"
              label="Rule"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchLogs"
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="2">
            <v-select
              v-model="filterDryRun"
              :items="dryRunOptions"
              label="Type"
              density="compact"
              hide-details
              clearable
              @update:model-value="fetchLogs"
            ></v-select>
          </v-col>
          <v-col cols="auto">
            <v-btn icon @click="fetchLogs" :loading="loading">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Logs Table -->
    <v-card>
      <v-data-table-server
        v-model:items-per-page="perPage"
        v-model:page="page"
        :headers="headers"
        :items="logs"
        :items-length="total"
        :loading="loading"
        :items-per-page-options="[25, 50, 100]"
        @update:options="onTableOptions"
      >
        <template v-slot:item.created_at="{ item }">
          {{ formatDate(item.created_at) }}
        </template>

        <template v-slot:item.torrent_name="{ item }">
          <div class="text-truncate" style="max-width: 250px;">
            <v-tooltip :text="item.torrent_name" location="top">
              <template v-slot:activator="{ props }">
                <span v-bind="props">{{ item.torrent_name }}</span>
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

        <template v-slot:item.rule_name="{ item }">
          <span v-if="item.rule_name">{{ item.rule_name }}</span>
          <span v-else class="text-medium-emphasis">Manual</span>
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
          <v-chip
            v-if="item.dry_run"
            color="info"
            size="small"
            label
          >
            DRY RUN
          </v-chip>
        </template>

        <template v-slot:item.reason="{ item }">
          <div class="text-truncate" style="max-width: 200px;">
            <v-tooltip :text="item.reason" location="top">
              <template v-slot:activator="{ props }">
                <span v-bind="props">{{ item.reason }}</span>
              </template>
            </v-tooltip>
          </div>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { systemApi } from '@/api'
import { useTrackersStore } from '@/stores/trackers'
import { useRulesStore } from '@/stores/rules'
import { format } from 'date-fns'

const trackersStore = useTrackersStore()
const rulesStore = useRulesStore()

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const page = ref(1)
const perPage = ref(50)

const filterAction = ref(null)
const filterTracker = ref(null)
const filterRule = ref(null)
const filterDryRun = ref(null)

const trackerOptions = ref([])
const ruleOptions = ref([])

const actionOptions = [
  { title: 'Deleted', value: 'deleted' },
  { title: 'Paused', value: 'paused' },
  { title: 'Tagged', value: 'tagged' },
  { title: 'Protected', value: 'protected' },
  { title: 'Unprotected', value: 'unprotected' },
]

const dryRunOptions = [
  { title: 'Real Actions', value: false },
  { title: 'Dry Run Only', value: true },
]

const headers = [
  { title: 'Date', key: 'created_at', width: '150px' },
  { title: 'Torrent', key: 'torrent_name' },
  { title: 'Tracker', key: 'tracker_name', width: '120px' },
  { title: 'Rule', key: 'rule_name', width: '150px' },
  { title: 'Action', key: 'action', width: '100px' },
  { title: '', key: 'dry_run', width: '100px' },
  { title: 'Reason', key: 'reason' },
]

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      per_page: perPage.value,
    }
    if (filterAction.value) params.action = filterAction.value
    if (filterTracker.value) params.tracker_id = filterTracker.value
    if (filterRule.value) params.rule_id = filterRule.value
    if (filterDryRun.value !== null) params.dry_run = filterDryRun.value

    const response = await systemApi.logs(params)
    logs.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  } finally {
    loading.value = false
  }
}

const loadFilters = async () => {
  await Promise.all([
    trackersStore.fetch(),
    rulesStore.fetch(),
  ])

  trackerOptions.value = trackersStore.trackers.map(t => ({
    title: t.name,
    value: t.id,
  }))

  ruleOptions.value = rulesStore.rules.map(r => ({
    title: r.name,
    value: r.id,
  }))
}

const onTableOptions = ({ page: p, itemsPerPage }) => {
  page.value = p
  perPage.value = itemsPerPage
  fetchLogs()
}

const formatDate = (date) => {
  if (!date) return ''
  return format(new Date(date), 'MMM d, HH:mm:ss')
}

const getActionColor = (action) => {
  switch (action) {
    case 'deleted': return 'error'
    case 'paused': return 'warning'
    case 'tagged': return 'info'
    case 'protected': return 'success'
    case 'unprotected': return 'grey'
    default: return 'grey'
  }
}

const handleRefresh = () => {
  fetchLogs()
}

onMounted(() => {
  loadFilters()
  fetchLogs()
  window.addEventListener('refresh-data', handleRefresh)
})

onUnmounted(() => {
  window.removeEventListener('refresh-data', handleRefresh)
})
</script>
