<template>
  <div>
    <h2 class="mb-4">Settings</h2>

    <v-row>
      <v-col cols="12" md="6">
        <!-- General Settings -->
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-cog</v-icon>
            General
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model.number="settings.scan_interval_minutes"
              label="Scan Interval (minutes)"
              type="number"
              min="1"
              hint="How often to check torrents"
              persistent-hint
            ></v-text-field>

            <v-switch
              v-model="settings.dry_run_mode"
              label="Dry Run Mode"
              hint="When enabled, no actions will be executed"
              persistent-hint
              color="warning"
            ></v-switch>

            <v-switch
              v-model="settings.notifications_enabled"
              label="Notifications Enabled"
              color="primary"
            ></v-switch>
          </v-card-text>
        </v-card>

        <!-- Storage Settings -->
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-harddisk</v-icon>
            Storage
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model.number="settings.disk_space_threshold_percent"
              label="Disk Space Threshold (%)"
              type="number"
              min="0"
              max="100"
              hint="Warn when disk space falls below this percentage"
              persistent-hint
            ></v-text-field>

            <v-select
              v-model="settings.disk_space_action"
              :items="diskSpaceActions"
              label="Action when disk space is low"
            ></v-select>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <!-- Protection Settings -->
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-shield</v-icon>
            Protection
          </v-card-title>
          <v-card-text>
            <v-combobox
              v-model="settings.protected_categories"
              label="Protected Categories"
              multiple
              chips
              closable-chips
              hint="Torrents in these categories will never be deleted"
              persistent-hint
            ></v-combobox>

            <v-combobox
              v-model="settings.protected_tags"
              label="Protected Tags"
              multiple
              chips
              closable-chips
              hint="Torrents with these tags will never be deleted"
              persistent-hint
              class="mt-4"
            ></v-combobox>
          </v-card-text>
        </v-card>

        <!-- Interface Settings -->
        <v-card class="mb-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-palette</v-icon>
            Interface
          </v-card-title>
          <v-card-text>
            <v-select
              v-model="settings.theme"
              :items="themeOptions"
              label="Theme"
            ></v-select>

            <v-text-field
              v-model.number="settings.log_retention_days"
              label="Log Retention (days)"
              type="number"
              min="1"
              hint="How long to keep action logs"
              persistent-hint
            ></v-text-field>
          </v-card-text>
        </v-card>

        <!-- Backup/Restore -->
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-backup-restore</v-icon>
            Backup & Restore
          </v-card-title>
          <v-card-text>
            <p class="text-body-2 mb-4">
              Export your configuration (connections, trackers, rules, settings) to a JSON file for backup or migration.
            </p>
            <div class="d-flex gap-2">
              <v-btn color="primary" @click="exportBackup" :loading="exporting">
                <v-icon start>mdi-download</v-icon>
                Export Backup
              </v-btn>
              <v-btn color="secondary" @click="triggerImport">
                <v-icon start>mdi-upload</v-icon>
                Import Backup
              </v-btn>
              <input
                ref="fileInput"
                type="file"
                accept=".json"
                style="display: none"
                @change="importBackup"
              >
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Save Button -->
    <div class="d-flex justify-end mt-4">
      <v-btn color="primary" size="large" @click="saveSettings" :loading="saving">
        <v-icon start>mdi-content-save</v-icon>
        Save Settings
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject } from 'vue'
import { systemApi } from '@/api'

const showSnackbar = inject('showSnackbar')

const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const fileInput = ref(null)

const settings = reactive({
  scan_interval_minutes: 15,
  dry_run_mode: false,
  disk_space_threshold_percent: 10,
  disk_space_action: 'pause_lowest_priority',
  protected_categories: [],
  protected_tags: ['permaseed', 'important'],
  theme: 'auto',
  notifications_enabled: true,
  log_retention_days: 30,
})

const diskSpaceActions = [
  { title: 'Pause lowest priority torrents', value: 'pause_lowest_priority' },
  { title: 'Delete lowest priority torrents', value: 'delete_lowest_priority' },
  { title: 'Notify only', value: 'notify' },
  { title: 'Do nothing', value: 'none' },
]

const themeOptions = [
  { title: 'Auto (System)', value: 'auto' },
  { title: 'Light', value: 'light' },
  { title: 'Dark', value: 'dark' },
]

const fetchSettings = async () => {
  loading.value = true
  try {
    const response = await systemApi.settings()
    Object.assign(settings, response.data)
  } catch (error) {
    showSnackbar('Failed to load settings', 'error')
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await systemApi.updateSettings(settings)
    showSnackbar('Settings saved', 'success')
  } catch (error) {
    showSnackbar('Failed to save settings', 'error')
  } finally {
    saving.value = false
  }
}

const exportBackup = async () => {
  exporting.value = true
  try {
    const response = await systemApi.exportBackup()
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `seedarr_backup_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showSnackbar('Backup exported', 'success')
  } catch (error) {
    showSnackbar('Failed to export backup', 'error')
  } finally {
    exporting.value = false
  }
}

const triggerImport = () => {
  fileInput.value?.click()
}

const importBackup = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    const data = JSON.parse(text)
    await systemApi.importBackup(data)
    showSnackbar('Backup imported successfully', 'success')
    await fetchSettings()
  } catch (error) {
    showSnackbar('Failed to import backup', 'error')
  }

  // Reset file input
  event.target.value = ''
}

onMounted(() => {
  fetchSettings()
})
</script>
