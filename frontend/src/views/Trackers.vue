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

    <!-- Zone Summary Card -->
    <v-card class="mb-4" v-if="trackers.length > 0">
      <v-card-text>
        <div class="d-flex justify-space-around text-center">
          <div>
            <div class="text-h4 text-error">{{ zoneTotals.zone1 }}</div>
            <div class="text-caption">Zone 1 - Obligations</div>
          </div>
          <v-divider vertical></v-divider>
          <div>
            <div class="text-h4 text-warning">{{ zoneTotals.zone2 }}</div>
            <div class="text-caption">Zone 2 - Preferences</div>
          </div>
          <v-divider vertical></v-divider>
          <div>
            <div class="text-h4 text-success">{{ zoneTotals.zone3 }}</div>
            <div class="text-caption">Zone 3 - Eligible</div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Loading State -->
    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4"></v-progress-linear>

    <!-- Tracker Cards -->
    <v-row>
      <v-col v-for="tracker in trackers" :key="tracker.id" cols="12" md="6" lg="4">
        <v-card :class="{ 'opacity-50': !tracker.enabled }">
          <!-- Header -->
          <v-card-title class="d-flex justify-space-between align-center">
            <div class="d-flex align-center">
              <v-icon :color="tracker.enabled ? 'success' : 'grey'" class="mr-2">
                {{ tracker.enabled ? 'mdi-check-circle' : 'mdi-close-circle' }}
              </v-icon>
              {{ tracker.name }}
            </div>
            <div class="d-flex">
              <v-btn
                icon
                variant="text"
                size="small"
                :color="tracker.permaseed ? 'primary' : 'grey'"
                @click="togglePermaseed(tracker)"
                :title="tracker.permaseed ? 'Permaseed enabled' : 'Click to enable permaseed'"
              >
                <v-icon>mdi-infinity</v-icon>
              </v-btn>
              <v-btn icon variant="text" size="small" @click="openDialog(tracker)">
                <v-icon>mdi-pencil</v-icon>
              </v-btn>
              <v-menu>
                <template v-slot:activator="{ props }">
                  <v-btn icon variant="text" size="small" v-bind="props">
                    <v-icon>mdi-dots-vertical</v-icon>
                  </v-btn>
                </template>
                <v-list density="compact">
                  <v-list-item @click="toggleTracker(tracker)">
                    <v-list-item-title>{{ tracker.enabled ? 'Disable' : 'Enable' }}</v-list-item-title>
                  </v-list-item>
                  <v-list-item @click="showStats(tracker)">
                    <v-list-item-title>View Stats</v-list-item-title>
                  </v-list-item>
                  <v-divider></v-divider>
                  <v-list-item @click="confirmDelete(tracker)" class="text-error">
                    <v-list-item-title>Delete</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>
          </v-card-title>

          <v-divider></v-divider>

          <!-- Zone Counters -->
          <v-card-text class="pa-2">
            <div class="d-flex justify-space-around text-center">
              <v-chip color="error" variant="flat" size="small">
                Z1: {{ tracker.stats_zone1_count }}
              </v-chip>
              <v-chip color="warning" variant="flat" size="small">
                Z2: {{ tracker.stats_zone2_count }}
              </v-chip>
              <v-chip color="success" variant="flat" size="small">
                Z3: {{ tracker.stats_zone3_count }}
              </v-chip>
            </div>
          </v-card-text>

          <v-divider></v-divider>

          <!-- Zone 1: Obligations -->
          <v-card-text class="pa-3 zone-section zone-1">
            <div class="d-flex align-center mb-2">
              <v-icon color="error" size="small" class="mr-2">mdi-shield-lock</v-icon>
              <span class="text-subtitle-2 text-error">Zone 1: Obligations</span>
            </div>
            <div class="text-body-2 ml-6">
              <span>Seed {{ tracker.min_seed_time_hours }}h</span>
              <v-chip size="x-small" class="mx-1" :color="tracker.min_operator === 'AND' ? 'error' : 'warning'">
                {{ tracker.min_operator }}
              </v-chip>
              <span>Ratio {{ tracker.min_ratio }}</span>
            </div>
          </v-card-text>

          <!-- Zone 2: Preferences -->
          <v-card-text class="pa-3 zone-section zone-2">
            <div class="d-flex align-center mb-2">
              <v-icon color="warning" size="small" class="mr-2">mdi-heart</v-icon>
              <span class="text-subtitle-2 text-warning">Zone 2: Preferences</span>
            </div>
            <div class="text-body-2 ml-6">
              <div v-if="tracker.keep_if_seeders_below">
                Keep if seeders &lt; {{ tracker.keep_if_seeders_below }}
              </div>
              <div v-if="tracker.keep_if_activity_within_hours">
                Keep if activity within {{ tracker.keep_if_activity_within_hours }}h
              </div>
              <div v-if="tracker.permaseed" class="text-primary font-weight-bold">
                <v-icon size="x-small">mdi-infinity</v-icon> Permaseed enabled
              </div>
              <div v-if="!tracker.keep_if_seeders_below && !tracker.keep_if_activity_within_hours && !tracker.permaseed" class="text-grey">
                No preferences set
              </div>
            </div>
          </v-card-text>

          <!-- Zone 3: Deletion -->
          <v-card-text class="pa-3 zone-section zone-3">
            <div class="d-flex align-center mb-2">
              <v-icon color="success" size="small" class="mr-2">mdi-delete-clock</v-icon>
              <span class="text-subtitle-2 text-success">Zone 3: Deletion</span>
            </div>
            <div class="text-body-2 ml-6">
              <div>Priority: {{ tracker.deletion_priority }}</div>
              <div v-if="tracker.max_seed_time_hours">
                Max seed time: {{ tracker.max_seed_time_hours }}h
              </div>
              <div v-else class="text-grey">No max seed time</div>
            </div>
          </v-card-text>

          <!-- Patterns Footer -->
          <v-divider></v-divider>
          <v-card-text class="pa-2">
            <v-chip
              v-for="pattern in tracker.patterns.slice(0, 3)"
              :key="pattern"
              size="x-small"
              class="mr-1"
              label
            >
              {{ pattern }}
            </v-chip>
            <v-chip v-if="tracker.patterns.length > 3" size="x-small" label>
              +{{ tracker.patterns.length - 3 }}
            </v-chip>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Empty State -->
    <v-card v-if="!loading && trackers.length === 0">
      <v-card-text class="text-center pa-8">
        <v-icon size="64" color="grey">mdi-server-off</v-icon>
        <h3 class="mt-4">No trackers configured</h3>
        <p class="text-grey">Click "Discover" to auto-detect trackers from qBittorrent and Prowlarr</p>
      </v-card-text>
    </v-card>

    <!-- Tracker Dialog (Edit/Create) -->
    <v-dialog v-model="dialog" max-width="700" scrollable>
      <v-card>
        <v-card-title>{{ editingTracker ? 'Edit Tracker' : 'New Tracker' }}</v-card-title>
        <v-divider></v-divider>
        <v-card-text class="pa-4" style="max-height: 70vh;">
          <v-form ref="formRef" v-model="formValid">
            <!-- Basic Info -->
            <div class="text-subtitle-1 font-weight-bold mb-2">Basic Information</div>
            <v-text-field
              v-model="form.name"
              label="Name"
              :rules="[v => !!v || 'Name is required']"
              required
              density="compact"
            ></v-text-field>

            <v-combobox
              v-model="form.patterns"
              label="URL Patterns"
              multiple
              chips
              closable-chips
              hint="Add domain patterns (e.g., tracker.example.com)"
              persistent-hint
              density="compact"
            ></v-combobox>

            <v-switch
              v-model="form.enabled"
              label="Enabled"
              color="success"
              hide-details
              class="mt-2"
            ></v-switch>

            <v-divider class="my-4"></v-divider>

            <!-- Zone 1: Obligations -->
            <div class="zone-header zone-1-header mb-3">
              <v-icon color="error" class="mr-2">mdi-shield-lock</v-icon>
              <span class="text-subtitle-1 font-weight-bold text-error">Zone 1: Obligations</span>
              <span class="text-caption ml-2">(Never delete before these conditions)</span>
            </div>

            <v-row>
              <v-col cols="4">
                <v-text-field
                  v-model.number="form.min_seed_time_hours"
                  label="Min Seed Time (hours)"
                  type="number"
                  :rules="[v => v >= 0 || 'Must be positive']"
                  hint="168 = 7 days"
                  persistent-hint
                  density="compact"
                ></v-text-field>
              </v-col>
              <v-col cols="4">
                <v-select
                  v-model="form.min_operator"
                  label="Operator"
                  :items="['AND', 'OR']"
                  hint="AND = both, OR = either"
                  persistent-hint
                  density="compact"
                ></v-select>
              </v-col>
              <v-col cols="4">
                <v-text-field
                  v-model.number="form.min_ratio"
                  label="Min Ratio"
                  type="number"
                  step="0.1"
                  :rules="[v => v >= 0 || 'Must be positive']"
                  density="compact"
                ></v-text-field>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>

            <!-- Zone 2: Preferences -->
            <div class="zone-header zone-2-header mb-3">
              <v-icon color="warning" class="mr-2">mdi-heart</v-icon>
              <span class="text-subtitle-1 font-weight-bold text-warning">Zone 2: Preferences</span>
              <span class="text-caption ml-2">(Keep longer if possible)</span>
            </div>

            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.keep_if_seeders_below"
                  label="Keep if Seeders Below"
                  type="number"
                  hint="Protect rare torrents"
                  persistent-hint
                  clearable
                  density="compact"
                ></v-text-field>
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.keep_if_activity_within_hours"
                  label="Keep if Activity Within (hours)"
                  type="number"
                  hint="Recent upload activity"
                  persistent-hint
                  clearable
                  density="compact"
                ></v-text-field>
              </v-col>
            </v-row>

            <v-switch
              v-model="form.permaseed"
              label="Permaseed (Never delete from this tracker)"
              color="primary"
              hide-details
            ></v-switch>

            <v-divider class="my-4"></v-divider>

            <!-- Zone 3: Deletion -->
            <div class="zone-header zone-3-header mb-3">
              <v-icon color="success" class="mr-2">mdi-delete-clock</v-icon>
              <span class="text-subtitle-1 font-weight-bold text-success">Zone 3: Deletion Settings</span>
              <span class="text-caption ml-2">(When disk space cleanup is needed)</span>
            </div>

            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.deletion_priority"
                  label="Deletion Priority (1-100)"
                  type="number"
                  :rules="[v => v >= 1 && v <= 100 || 'Must be 1-100']"
                  hint="Higher = delete first"
                  persistent-hint
                  density="compact"
                ></v-text-field>
              </v-col>
              <v-col cols="6">
                <v-text-field
                  v-model.number="form.max_seed_time_hours"
                  label="Max Seed Time (hours)"
                  type="number"
                  hint="Force delete after (optional)"
                  persistent-hint
                  clearable
                  density="compact"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider></v-divider>
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
            <template v-slot:item.prowlarr_indexer_name="{ item }">
              <span v-if="item.prowlarr_indexer_name">{{ item.prowlarr_indexer_name }}</span>
              <span v-else class="text-grey">-</span>
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
          <!-- Zone Distribution -->
          <h4 class="mb-2">Zone Distribution</h4>
          <div class="d-flex justify-space-around text-center mb-4">
            <v-chip color="error" variant="flat">
              Z1: {{ selectedStats.zone1_count }}
            </v-chip>
            <v-chip color="warning" variant="flat">
              Z2: {{ selectedStats.zone2_count }}
            </v-chip>
            <v-chip color="success" variant="flat">
              Z3: {{ selectedStats.zone3_count }}
            </v-chip>
          </div>

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
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useTrackersStore } from '@/stores/trackers'

const showSnackbar = inject('showSnackbar')
const trackersStore = useTrackersStore()

const loading = ref(false)
const trackers = ref([])

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
  enabled: true,
  // Zone 1
  min_seed_time_hours: 168,
  min_ratio: 1.0,
  min_operator: 'OR',
  // Zone 2
  keep_if_seeders_below: 5,
  keep_if_activity_within_hours: 72,
  permaseed: false,
  // Zone 3
  deletion_priority: 50,
  max_seed_time_hours: null,
})

const zoneTotals = computed(() => {
  return {
    zone1: trackers.value.reduce((sum, t) => sum + (t.stats_zone1_count || 0), 0),
    zone2: trackers.value.reduce((sum, t) => sum + (t.stats_zone2_count || 0), 0),
    zone3: trackers.value.reduce((sum, t) => sum + (t.stats_zone3_count || 0), 0),
  }
})

const discoveryHeaders = [
  { title: '', key: 'already_exists', width: '40px' },
  { title: 'Name', key: 'name' },
  { title: 'Prowlarr', key: 'prowlarr_indexer_name' },
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
    form.enabled = tracker.enabled
    // Zone 1
    form.min_seed_time_hours = tracker.min_seed_time_hours
    form.min_ratio = tracker.min_ratio
    form.min_operator = tracker.min_operator
    // Zone 2
    form.keep_if_seeders_below = tracker.keep_if_seeders_below
    form.keep_if_activity_within_hours = tracker.keep_if_activity_within_hours
    form.permaseed = tracker.permaseed
    // Zone 3
    form.deletion_priority = tracker.deletion_priority
    form.max_seed_time_hours = tracker.max_seed_time_hours
  } else {
    form.name = ''
    form.patterns = []
    form.enabled = true
    form.min_seed_time_hours = 168
    form.min_ratio = 1.0
    form.min_operator = 'OR'
    form.keep_if_seeders_below = 5
    form.keep_if_activity_within_hours = 72
    form.permaseed = false
    form.deletion_priority = 50
    form.max_seed_time_hours = null
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

const toggleTracker = async (tracker) => {
  try {
    await trackersStore.toggle(tracker.id)
    trackers.value = trackersStore.trackers
    showSnackbar(`Tracker ${tracker.enabled ? 'disabled' : 'enabled'}`, 'success')
  } catch (error) {
    showSnackbar('Failed to toggle tracker', 'error')
  }
}

const togglePermaseed = async (tracker) => {
  try {
    await trackersStore.togglePermaseed(tracker.id)
    trackers.value = trackersStore.trackers
    showSnackbar(`Permaseed ${tracker.permaseed ? 'disabled' : 'enabled'}`, 'success')
  } catch (error) {
    showSnackbar('Failed to toggle permaseed', 'error')
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
      prowlarr_indexer_name: tracker.prowlarr_indexer_name,
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
})
</script>

<style scoped>
.zone-section {
  border-left: 3px solid transparent;
}

.zone-1 {
  border-left-color: rgb(var(--v-theme-error));
  background-color: rgba(var(--v-theme-error), 0.05);
}

.zone-2 {
  border-left-color: rgb(var(--v-theme-warning));
  background-color: rgba(var(--v-theme-warning), 0.05);
}

.zone-3 {
  border-left-color: rgb(var(--v-theme-success));
  background-color: rgba(var(--v-theme-success), 0.05);
}

.zone-header {
  display: flex;
  align-items: center;
}

.zone-1-header {
  border-left: 4px solid rgb(var(--v-theme-error));
  padding-left: 8px;
}

.zone-2-header {
  border-left: 4px solid rgb(var(--v-theme-warning));
  padding-left: 8px;
}

.zone-3-header {
  border-left: 4px solid rgb(var(--v-theme-success));
  padding-left: 8px;
}
</style>
