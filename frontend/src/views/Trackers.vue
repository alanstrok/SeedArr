<template>
  <div>
    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-4">
      <h2>Trackers</h2>
      <div>
        <v-btn color="secondary" class="mr-2" @click="discoverTrackers" :loading="discovering">
          <v-icon start>mdi-radar</v-icon>
          Discover
        </v-btn>
        <v-btn color="primary" @click="openDialog()">
          <v-icon start>mdi-plus</v-icon>
          New Tracker
        </v-btn>
      </div>
    </div>

    <!-- Trackers Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="trackers"
        :loading="loading"
        item-value="id"
      >
        <template v-slot:item.patterns="{ item }">
          <v-chip
            v-for="pattern in item.patterns"
            :key="pattern"
            size="small"
            class="mr-1"
            label
          >
            {{ pattern }}
          </v-chip>
        </template>

        <template v-slot:item.stats_ratio="{ item }">
          {{ item.stats_ratio.toFixed(2) }}
        </template>

        <template v-slot:item.stats_upload="{ item }">
          {{ formatBytes(item.stats_upload) }}
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn icon size="small" variant="text" @click="showStats(item)">
            <v-icon>mdi-chart-bar</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" @click="openDialog(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" color="error" @click="confirmDelete(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- Tracker Dialog -->
    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>{{ editingTracker ? 'Edit Tracker' : 'New Tracker' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef" v-model="formValid">
            <v-text-field
              v-model="form.name"
              label="Name"
              :rules="[v => !!v || 'Name is required']"
              required
            ></v-text-field>

            <v-combobox
              v-model="form.patterns"
              label="URL Patterns"
              multiple
              chips
              closable-chips
              hint="Add domain patterns (e.g., tracker.example.com)"
              persistent-hint
            ></v-combobox>

            <v-select
              v-model="form.default_rule_id"
              :items="ruleOptions"
              label="Default Rule"
              clearable
              class="mt-4"
            ></v-select>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveTracker" :loading="saving" :disabled="!formValid">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Discovery Dialog -->
    <v-dialog v-model="discoveryDialog" max-width="800">
      <v-card>
        <v-card-title>Discovered Trackers</v-card-title>
        <v-card-text>
          <v-alert v-if="discoveredTrackers.length === 0" type="info">
            No new trackers discovered. All trackers from qBittorrent and Prowlarr are already configured.
          </v-alert>

          <v-data-table
            v-else
            :headers="discoveryHeaders"
            :items="discoveredTrackers"
            density="compact"
          >
            <template v-slot:item.already_exists="{ item }">
              <v-icon v-if="item.already_exists" color="success">mdi-check</v-icon>
              <v-icon v-else color="warning">mdi-new-box</v-icon>
            </template>
            <template v-slot:item.actions="{ item }">
              <v-btn
                v-if="!item.already_exists"
                size="small"
                color="primary"
                @click="addDiscoveredTracker(item)"
              >
                Add
              </v-btn>
              <span v-else class="text-success">Already added</span>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="discoveryDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Stats Dialog -->
    <v-dialog v-model="statsDialog" max-width="600">
      <v-card v-if="selectedStats">
        <v-card-title>{{ selectedStats.name }} - Statistics</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h4">{{ selectedStats.total_torrents }}</div>
                  <div class="text-caption">Total Torrents</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="6">
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h4">{{ selectedStats.active_torrents }}</div>
                  <div class="text-caption">Active Torrents</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="6">
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h4">{{ formatBytes(selectedStats.total_upload) }}</div>
                  <div class="text-caption">Total Upload</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="6">
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h4">{{ selectedStats.average_ratio.toFixed(2) }}</div>
                  <div class="text-caption">Average Ratio</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <h4 class="mt-4 mb-2">Top Categories</h4>
          <v-list density="compact">
            <v-list-item v-for="cat in selectedStats.top_categories" :key="cat.name">
              <v-list-item-title>{{ cat.name }}</v-list-item-title>
              <template v-slot:append>
                <v-chip size="small">{{ cat.count }}</v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="statsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Tracker</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ trackerToDelete?.name }}"?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteTracker" :loading="deleting">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject } from 'vue'
import { useTrackersStore } from '@/stores/trackers'
import { useRulesStore } from '@/stores/rules'

const showSnackbar = inject('showSnackbar')
const trackersStore = useTrackersStore()
const rulesStore = useRulesStore()

const loading = ref(false)
const trackers = ref([])
const ruleOptions = ref([])

const dialog = ref(false)
const formRef = ref(null)
const formValid = ref(false)
const editingTracker = ref(null)
const saving = ref(false)

const discoveryDialog = ref(false)
const discoveredTrackers = ref([])
const discovering = ref(false)

const statsDialog = ref(false)
const selectedStats = ref(null)

const deleteDialog = ref(false)
const trackerToDelete = ref(null)
const deleting = ref(false)

const form = reactive({
  name: '',
  patterns: [],
  default_rule_id: null,
})

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Patterns', key: 'patterns' },
  { title: 'Torrents', key: 'stats_torrent_count', width: '100px' },
  { title: 'Avg Ratio', key: 'stats_ratio', width: '100px' },
  { title: 'Upload', key: 'stats_upload', width: '120px' },
  { title: 'Actions', key: 'actions', width: '140px', sortable: false },
]

const discoveryHeaders = [
  { title: '', key: 'already_exists', width: '40px' },
  { title: 'Name', key: 'name' },
  { title: 'Patterns', key: 'patterns' },
  { title: 'Torrents', key: 'torrent_count', width: '100px' },
  { title: '', key: 'actions', width: '100px' },
]

const fetchTrackers = async () => {
  loading.value = true
  try {
    await trackersStore.fetch()
    trackers.value = trackersStore.trackers
  } catch (error) {
    showSnackbar('Failed to load trackers', 'error')
  } finally {
    loading.value = false
  }
}

const openDialog = (tracker = null) => {
  editingTracker.value = tracker
  if (tracker) {
    form.name = tracker.name
    form.patterns = [...tracker.patterns]
    form.default_rule_id = tracker.default_rule_id
  } else {
    form.name = ''
    form.patterns = []
    form.default_rule_id = null
  }
  dialog.value = true
}

const saveTracker = async () => {
  saving.value = true
  try {
    if (editingTracker.value) {
      await trackersStore.update(editingTracker.value.id, form)
      showSnackbar('Tracker updated', 'success')
    } else {
      await trackersStore.create(form)
      showSnackbar('Tracker created', 'success')
    }
    trackers.value = trackersStore.trackers
    dialog.value = false
  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Failed to save tracker', 'error')
  } finally {
    saving.value = false
  }
}

const discoverTrackers = async () => {
  discovering.value = true
  try {
    discoveredTrackers.value = await trackersStore.discover()
    discoveryDialog.value = true
  } catch (error) {
    showSnackbar('Failed to discover trackers', 'error')
  } finally {
    discovering.value = false
  }
}

const addDiscoveredTracker = async (tracker) => {
  try {
    await trackersStore.create({
      name: tracker.name,
      patterns: tracker.patterns,
      prowlarr_indexer_id: tracker.prowlarr_indexer_id,
    })
    tracker.already_exists = true
    trackers.value = trackersStore.trackers
    showSnackbar('Tracker added', 'success')
  } catch (error) {
    showSnackbar('Failed to add tracker', 'error')
  }
}

const showStats = async (tracker) => {
  try {
    selectedStats.value = await trackersStore.getStats(tracker.id)
    statsDialog.value = true
  } catch (error) {
    showSnackbar('Failed to load stats', 'error')
  }
}

const confirmDelete = (tracker) => {
  trackerToDelete.value = tracker
  deleteDialog.value = true
}

const deleteTracker = async () => {
  deleting.value = true
  try {
    await trackersStore.delete(trackerToDelete.value.id)
    trackers.value = trackersStore.trackers
    deleteDialog.value = false
    showSnackbar('Tracker deleted', 'success')
  } catch (error) {
    showSnackbar('Failed to delete tracker', 'error')
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

onMounted(async () => {
  await fetchTrackers()
  await rulesStore.fetch()
  ruleOptions.value = rulesStore.rules.map(r => ({
    title: r.name,
    value: r.id,
  }))
})
</script>
