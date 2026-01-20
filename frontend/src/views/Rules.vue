<template>
  <div>
    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-4">
      <h2>Seeding Rules</h2>
      <v-btn color="primary" @click="openDialog()">
        <v-icon start>mdi-plus</v-icon>
        New Rule
      </v-btn>
    </div>

    <!-- Rules List -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="rules"
        :loading="loading"
        item-value="id"
      >
        <template v-slot:item.priority="{ item }">
          <v-chip size="small" label>{{ item.priority }}</v-chip>
        </template>

        <template v-slot:item.conditions="{ item }">
          <div class="text-caption">
            <span v-if="item.conditions.tracker_ids?.length">
              {{ item.conditions.tracker_ids.length }} tracker(s)
            </span>
            <span v-if="item.conditions.categories?.length">
              {{ item.conditions.categories.join(', ') }}
            </span>
            <span v-if="!item.conditions.tracker_ids?.length && !item.conditions.categories?.length">
              All torrents
            </span>
          </div>
        </template>

        <template v-slot:item.criteria="{ item }">
          <div class="text-caption">
            <span v-if="item.criteria.min_ratio">Ratio >= {{ item.criteria.min_ratio }}</span>
            <span v-if="item.criteria.min_ratio && item.criteria.min_seed_time_minutes"> {{ item.criteria.operator }} </span>
            <span v-if="item.criteria.min_seed_time_minutes">Time >= {{ formatMinutes(item.criteria.min_seed_time_minutes) }}</span>
          </div>
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

        <template v-slot:item.enabled="{ item }">
          <v-switch
            :model-value="item.enabled"
            hide-details
            density="compact"
            color="success"
            @update:model-value="toggleEnabled(item)"
          ></v-switch>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn icon size="small" variant="text" @click="testRule(item)">
            <v-icon>mdi-test-tube</v-icon>
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

    <!-- Rule Dialog -->
    <v-dialog v-model="dialog" max-width="800" persistent>
      <v-card>
        <v-card-title>{{ editingRule ? 'Edit Rule' : 'New Rule' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef" v-model="formValid">
            <v-row>
              <v-col cols="12" md="8">
                <v-text-field
                  v-model="form.name"
                  label="Rule Name"
                  :rules="[v => !!v || 'Name is required']"
                  required
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model.number="form.priority"
                  label="Priority"
                  type="number"
                  min="1"
                  hint="Lower = Higher priority"
                ></v-text-field>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-3">Conditions (Which torrents to match)</h4>

            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="form.conditions.tracker_ids"
                  :items="trackerOptions"
                  label="Trackers"
                  multiple
                  chips
                  closable-chips
                  hint="Leave empty for all trackers"
                  persistent-hint
                ></v-select>
              </v-col>
              <v-col cols="12" md="6">
                <v-combobox
                  v-model="form.conditions.categories"
                  label="Categories"
                  multiple
                  chips
                  closable-chips
                  hint="Leave empty for all categories"
                  persistent-hint
                ></v-combobox>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="form.conditions.min_size_gb"
                  label="Min Size (GB)"
                  type="number"
                  min="0"
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="form.conditions.max_size_gb"
                  label="Max Size (GB)"
                  type="number"
                  min="0"
                ></v-text-field>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-3">Criteria (When to take action)</h4>

            <v-row>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model.number="form.criteria.min_ratio"
                  label="Minimum Ratio"
                  type="number"
                  step="0.1"
                  min="0"
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model.number="form.criteria.min_seed_time_minutes"
                  label="Min Seed Time (minutes)"
                  type="number"
                  min="0"
                  hint="e.g., 10080 = 7 days"
                  persistent-hint
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="4">
                <v-select
                  v-model="form.criteria.operator"
                  :items="['AND', 'OR']"
                  label="Operator"
                  hint="AND = all required, OR = any one"
                  persistent-hint
                ></v-select>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-3">Exceptions (Do not act if)</h4>

            <v-row>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="form.exceptions.keep_if_seeders_below"
                  label="Keep if seeders below"
                  type="number"
                  min="0"
                  hint="Protect rare torrents"
                  persistent-hint
                ></v-text-field>
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="form.exceptions.keep_if_last_activity_days"
                  label="Keep if active within (days)"
                  type="number"
                  min="0"
                  hint="Protect recently active torrents"
                  persistent-hint
                ></v-text-field>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>
            <h4 class="mb-3">Action</h4>

            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="form.action"
                  :items="actionOptions"
                  label="Action"
                ></v-select>
              </v-col>
              <v-col cols="12" md="6" v-if="form.action === 'tag'">
                <v-text-field
                  v-model="form.action_params.tag"
                  label="Tag Name"
                ></v-text-field>
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="12">
                <v-checkbox
                  v-model="form.notify"
                  label="Send notifications"
                  hide-details
                ></v-checkbox>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveRule" :loading="saving" :disabled="!formValid">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Test Result Dialog -->
    <v-dialog v-model="testDialog" max-width="800">
      <v-card>
        <v-card-title>Rule Test Results</v-card-title>
        <v-card-text>
          <v-alert v-if="testResult" type="info" class="mb-4">
            {{ testResult.total_matched }} torrents matched:
            {{ testResult.would_be_deleted }} would be deleted,
            {{ testResult.would_be_paused }} would be paused,
            {{ testResult.would_be_tagged }} would be tagged,
            {{ testResult.protected_count }} protected
          </v-alert>

          <v-data-table
            :headers="testHeaders"
            :items="testResult?.matched_torrents || []"
            :loading="testing"
            density="compact"
            :items-per-page="10"
          >
            <template v-slot:item.would_act="{ item }">
              <v-icon :color="item.would_act ? 'success' : 'grey'">
                {{ item.would_act ? 'mdi-check' : 'mdi-shield' }}
              </v-icon>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="testDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Rule</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ ruleToDelete?.name }}"?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteRule" :loading="deleting">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject } from 'vue'
import { useRulesStore } from '@/stores/rules'
import { useTrackersStore } from '@/stores/trackers'
import { rulesApi } from '@/api'

const showSnackbar = inject('showSnackbar')
const rulesStore = useRulesStore()
const trackersStore = useTrackersStore()

const loading = ref(false)
const rules = ref([])
const trackerOptions = ref([])

const dialog = ref(false)
const formRef = ref(null)
const formValid = ref(false)
const editingRule = ref(null)
const saving = ref(false)

const testDialog = ref(false)
const testResult = ref(null)
const testing = ref(false)

const deleteDialog = ref(false)
const ruleToDelete = ref(null)
const deleting = ref(false)

const defaultForm = {
  name: '',
  priority: 100,
  enabled: true,
  conditions: {
    tracker_ids: [],
    categories: [],
    tags: [],
    min_size_gb: null,
    max_size_gb: null,
  },
  criteria: {
    min_ratio: 1.0,
    min_seed_time_minutes: 10080,
    max_seed_time_minutes: null,
    operator: 'AND',
  },
  exceptions: {
    keep_if_seeders_below: null,
    keep_if_last_activity_days: null,
  },
  action: 'delete',
  action_params: {},
  notify: false,
  notify_connections: [],
}

const form = reactive({ ...defaultForm })

const headers = [
  { title: 'Priority', key: 'priority', width: '80px' },
  { title: 'Name', key: 'name' },
  { title: 'Conditions', key: 'conditions' },
  { title: 'Criteria', key: 'criteria' },
  { title: 'Action', key: 'action', width: '100px' },
  { title: 'Enabled', key: 'enabled', width: '100px' },
  { title: 'Actions', key: 'actions', width: '140px', sortable: false },
]

const testHeaders = [
  { title: 'Name', key: 'name' },
  { title: 'Tracker', key: 'tracker_name' },
  { title: 'Ratio', key: 'ratio' },
  { title: 'Seed Time', key: 'seed_time_minutes' },
  { title: 'Would Act', key: 'would_act', width: '80px' },
  { title: 'Reason', key: 'reason' },
]

const actionOptions = [
  { title: 'Delete (with files)', value: 'delete' },
  { title: 'Delete (keep files)', value: 'delete_torrent_only' },
  { title: 'Pause', value: 'pause' },
  { title: 'Add Tag', value: 'tag' },
]

const fetchRules = async () => {
  loading.value = true
  try {
    await rulesStore.fetch()
    rules.value = rulesStore.sortedRules
  } catch (error) {
    showSnackbar('Failed to load rules', 'error')
  } finally {
    loading.value = false
  }
}

const openDialog = (rule = null) => {
  editingRule.value = rule
  if (rule) {
    Object.assign(form, {
      name: rule.name,
      priority: rule.priority,
      enabled: rule.enabled,
      conditions: { ...defaultForm.conditions, ...rule.conditions },
      criteria: { ...defaultForm.criteria, ...rule.criteria },
      exceptions: { ...defaultForm.exceptions, ...rule.exceptions },
      action: rule.action,
      action_params: { ...rule.action_params },
      notify: rule.notify,
      notify_connections: [...rule.notify_connections],
    })
  } else {
    Object.assign(form, JSON.parse(JSON.stringify(defaultForm)))
  }
  dialog.value = true
}

const saveRule = async () => {
  saving.value = true
  try {
    const data = { ...form }
    if (editingRule.value) {
      await rulesStore.update(editingRule.value.id, data)
      showSnackbar('Rule updated', 'success')
    } else {
      await rulesStore.create(data)
      showSnackbar('Rule created', 'success')
    }
    rules.value = rulesStore.sortedRules
    dialog.value = false
  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Failed to save rule', 'error')
  } finally {
    saving.value = false
  }
}

const toggleEnabled = async (rule) => {
  try {
    await rulesStore.update(rule.id, { enabled: !rule.enabled })
    rule.enabled = !rule.enabled
  } catch (error) {
    showSnackbar('Failed to update rule', 'error')
  }
}

const testRule = async (rule) => {
  testing.value = true
  testDialog.value = true
  testResult.value = null
  try {
    testResult.value = await rulesStore.test(rule.id)
  } catch (error) {
    showSnackbar('Failed to test rule', 'error')
  } finally {
    testing.value = false
  }
}

const confirmDelete = (rule) => {
  ruleToDelete.value = rule
  deleteDialog.value = true
}

const deleteRule = async () => {
  deleting.value = true
  try {
    await rulesStore.delete(ruleToDelete.value.id)
    rules.value = rulesStore.sortedRules
    deleteDialog.value = false
    showSnackbar('Rule deleted', 'success')
  } catch (error) {
    showSnackbar('Failed to delete rule', 'error')
  } finally {
    deleting.value = false
  }
}

const formatMinutes = (minutes) => {
  if (minutes >= 1440) {
    const days = Math.floor(minutes / 1440)
    return `${days}d`
  }
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    return `${hours}h`
  }
  return `${minutes}m`
}

const getActionColor = (action) => {
  switch (action) {
    case 'delete':
    case 'delete_torrent_only':
      return 'error'
    case 'pause':
      return 'warning'
    case 'tag':
      return 'info'
    default:
      return 'grey'
  }
}

onMounted(async () => {
  await fetchRules()
  await trackersStore.fetch()
  trackerOptions.value = trackersStore.trackers.map(t => ({
    title: t.name,
    value: t.id,
  }))
})
</script>
