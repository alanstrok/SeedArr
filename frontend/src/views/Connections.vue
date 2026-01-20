<template>
  <div>
    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-4">
      <h2>Connections</h2>
      <v-btn color="primary" @click="openDialog()">
        <v-icon start>mdi-plus</v-icon>
        New Connection
      </v-btn>
    </div>

    <!-- Download Clients -->
    <h3 class="mb-2">Download Clients</h3>
    <v-card class="mb-4">
      <v-data-table
        :headers="headers"
        :items="qbittorrentConnections"
        :loading="loading"
        density="comfortable"
      >
        <template v-slot:item.type="{ item }">
          <v-chip size="small" color="primary" label>{{ item.type }}</v-chip>
        </template>
        <template v-slot:item.enabled="{ item }">
          <v-icon :color="item.enabled ? 'success' : 'grey'">
            {{ item.enabled ? 'mdi-check-circle' : 'mdi-circle-outline' }}
          </v-icon>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-btn icon size="small" variant="text" @click="testConnection(item)" :loading="testing === item.id">
            <v-icon>mdi-connection</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" @click="openDialog(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" color="error" @click="confirmDelete(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
        <template v-slot:no-data>
          <div class="text-center pa-4">
            <v-icon size="48" color="grey">mdi-download-box-outline</v-icon>
            <div class="mt-2">No download clients configured</div>
            <v-btn color="primary" class="mt-2" @click="openDialog(null, 'qbittorrent')">
              Add qBittorrent
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- *Arr Applications -->
    <h3 class="mb-2">*Arr Applications</h3>
    <v-card class="mb-4">
      <v-data-table
        :headers="headers"
        :items="arrConnections"
        :loading="loading"
        density="comfortable"
      >
        <template v-slot:item.type="{ item }">
          <v-chip size="small" color="info" label>{{ item.type }}</v-chip>
        </template>
        <template v-slot:item.enabled="{ item }">
          <v-icon :color="item.enabled ? 'success' : 'grey'">
            {{ item.enabled ? 'mdi-check-circle' : 'mdi-circle-outline' }}
          </v-icon>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-btn icon size="small" variant="text" @click="testConnection(item)" :loading="testing === item.id">
            <v-icon>mdi-connection</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" @click="openDialog(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" color="error" @click="confirmDelete(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
        <template v-slot:no-data>
          <div class="text-center pa-4 text-medium-emphasis">
            No *Arr applications configured (optional)
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Notifications -->
    <h3 class="mb-2">Notifications</h3>
    <v-card>
      <v-data-table
        :headers="headers"
        :items="notificationConnections"
        :loading="loading"
        density="comfortable"
      >
        <template v-slot:item.type="{ item }">
          <v-chip size="small" color="secondary" label>{{ item.type }}</v-chip>
        </template>
        <template v-slot:item.enabled="{ item }">
          <v-icon :color="item.enabled ? 'success' : 'grey'">
            {{ item.enabled ? 'mdi-check-circle' : 'mdi-circle-outline' }}
          </v-icon>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-btn icon size="small" variant="text" @click="testConnection(item)" :loading="testing === item.id">
            <v-icon>mdi-connection</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" @click="openDialog(item)">
            <v-icon>mdi-pencil</v-icon>
          </v-btn>
          <v-btn icon size="small" variant="text" color="error" @click="confirmDelete(item)">
            <v-icon>mdi-delete</v-icon>
          </v-btn>
        </template>
        <template v-slot:no-data>
          <div class="text-center pa-4 text-medium-emphasis">
            No notification services configured (optional)
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Connection Dialog -->
    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>{{ editingConnection ? 'Edit Connection' : 'New Connection' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef" v-model="formValid">
            <v-select
              v-model="form.type"
              :items="typeOptions"
              label="Type"
              :rules="[v => !!v || 'Type is required']"
              :disabled="!!editingConnection"
              required
            ></v-select>

            <v-text-field
              v-model="form.name"
              label="Name"
              :rules="[v => !!v || 'Name is required']"
              required
            ></v-text-field>

            <v-text-field
              v-model="form.url"
              :label="getUrlLabel(form.type)"
              :hint="getUrlHint(form.type)"
              persistent-hint
              :rules="[v => !!v || 'URL is required']"
              required
            ></v-text-field>

            <template v-if="['sonarr', 'radarr', 'prowlarr'].includes(form.type)">
              <v-text-field
                v-model="form.api_key"
                label="API Key"
                :rules="[v => !!v || 'API Key is required']"
                required
              ></v-text-field>
            </template>

            <template v-if="form.type === 'qbittorrent'">
              <v-text-field
                v-model="form.username"
                label="Username"
              ></v-text-field>
              <v-text-field
                v-model="form.password"
                label="Password"
                type="password"
              ></v-text-field>
            </template>

            <template v-if="form.type === 'telegram'">
              <v-text-field
                v-model="form.api_key"
                label="Chat ID"
                hint="Your Telegram chat ID"
                persistent-hint
              ></v-text-field>
            </template>

            <v-switch
              v-model="form.enabled"
              label="Enabled"
              color="success"
            ></v-switch>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveConnection" :loading="saving" :disabled="!formValid">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Connection</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ connectionToDelete?.name }}"?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteConnection" :loading="deleting">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useConnectionsStore } from '@/stores/connections'

const showSnackbar = inject('showSnackbar')
const connectionsStore = useConnectionsStore()

const loading = ref(false)
const testing = ref(null)

const dialog = ref(false)
const formRef = ref(null)
const formValid = ref(false)
const editingConnection = ref(null)
const saving = ref(false)

const deleteDialog = ref(false)
const connectionToDelete = ref(null)
const deleting = ref(false)

const form = reactive({
  type: '',
  name: '',
  url: '',
  api_key: '',
  username: '',
  password: '',
  enabled: true,
})

const headers = [
  { title: 'Type', key: 'type', width: '120px' },
  { title: 'Name', key: 'name' },
  { title: 'URL', key: 'url' },
  { title: 'Enabled', key: 'enabled', width: '80px' },
  { title: 'Actions', key: 'actions', width: '140px', sortable: false },
]

const typeOptions = [
  { title: 'qBittorrent', value: 'qbittorrent' },
  { title: 'Sonarr', value: 'sonarr' },
  { title: 'Radarr', value: 'radarr' },
  { title: 'Prowlarr', value: 'prowlarr' },
  { title: 'Discord', value: 'discord' },
  { title: 'Telegram', value: 'telegram' },
]

const qbittorrentConnections = computed(() => connectionsStore.qbittorrentConnections)
const arrConnections = computed(() => connectionsStore.arrConnections)
const notificationConnections = computed(() => connectionsStore.notificationConnections)

const getUrlLabel = (type) => {
  switch (type) {
    case 'discord': return 'Webhook URL'
    case 'telegram': return 'Bot Token'
    default: return 'URL'
  }
}

const getUrlHint = (type) => {
  switch (type) {
    case 'qbittorrent': return 'e.g., http://localhost:8080'
    case 'sonarr':
    case 'radarr':
    case 'prowlarr': return 'e.g., http://localhost:8989'
    case 'discord': return 'Discord webhook URL'
    case 'telegram': return 'Bot token from @BotFather'
    default: return ''
  }
}

const fetchConnections = async () => {
  loading.value = true
  try {
    await connectionsStore.fetch()
  } catch (error) {
    showSnackbar('Failed to load connections', 'error')
  } finally {
    loading.value = false
  }
}

const openDialog = (connection = null, defaultType = null) => {
  editingConnection.value = connection
  if (connection) {
    form.type = connection.type
    form.name = connection.name
    form.url = connection.url
    form.api_key = connection.api_key || ''
    form.username = connection.username || ''
    form.password = ''
    form.enabled = connection.enabled
  } else {
    form.type = defaultType || ''
    form.name = ''
    form.url = ''
    form.api_key = ''
    form.username = ''
    form.password = ''
    form.enabled = true
  }
  dialog.value = true
}

const saveConnection = async () => {
  saving.value = true
  try {
    const data = { ...form }
    // Don't send empty password on update
    if (editingConnection.value && !data.password) {
      delete data.password
    }

    if (editingConnection.value) {
      await connectionsStore.update(editingConnection.value.id, data)
      showSnackbar('Connection updated', 'success')
    } else {
      await connectionsStore.create(data)
      showSnackbar('Connection created', 'success')
    }
    dialog.value = false
  } catch (error) {
    showSnackbar(error.response?.data?.detail || 'Failed to save connection', 'error')
  } finally {
    saving.value = false
  }
}

const testConnection = async (connection) => {
  testing.value = connection.id
  try {
    const result = await connectionsStore.test(connection.id)
    if (result.success) {
      showSnackbar(`Connected successfully${result.details?.version ? ` (v${result.details.version})` : ''}`, 'success')
    } else {
      showSnackbar(result.message || 'Connection failed', 'error')
    }
  } catch (error) {
    showSnackbar('Test failed', 'error')
  } finally {
    testing.value = null
  }
}

const confirmDelete = (connection) => {
  connectionToDelete.value = connection
  deleteDialog.value = true
}

const deleteConnection = async () => {
  deleting.value = true
  try {
    await connectionsStore.delete(connectionToDelete.value.id)
    deleteDialog.value = false
    showSnackbar('Connection deleted', 'success')
  } catch (error) {
    showSnackbar('Failed to delete connection', 'error')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchConnections()
})
</script>
