<template>
  <div class="sqlbot-table-container sync-container">
    <div class="tool-left">
      <span class="page-title">{{ $t('sync.title') }}</span>
      <div class="search-bar">
        <el-button type="primary" @click="handleCreate()">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('sync.create') }}
        </el-button>
      </div>
    </div>

    <!-- Datasource cards -->
    <div v-loading="loading" class="sync-cards">
      <el-empty v-if="datasources.length === 0" :description="$t('sync.no_datasource')" />
      <el-card
        v-for="ds in datasources"
        :key="ds.id"
        class="sync-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <span class="ds-name">{{ ds.name }}</span>
            <el-tag :type="ds.enabled ? 'success' : 'info'" size="small">
              {{ ds.enabled ? $t('sync.enabled') : $t('sync.disabled') }}
            </el-tag>
          </div>
        </template>
        <div class="card-body">
          <div class="card-info">
            <span class="info-label">{{ $t('sync.db_type') }}:</span>
            <span>{{ ds.db_type }}</span>
          </div>
          <div class="card-info">
            <span class="info-label">{{ $t('sync.host') }}:</span>
            <span>{{ ds.host }}:{{ ds.port }}</span>
          </div>
          <div class="card-info">
            <span class="info-label">{{ $t('sync.database') }}:</span>
            <span>{{ ds.database }}</span>
          </div>
          <div class="card-info">
            <span class="info-label">{{ $t('sync.workspace') }}:</span>
            <span>{{ getWorkspaceName(ds.oid) }}</span>
          </div>
          <div class="card-info">
            <span class="info-label">{{ $t('sync.schedule') }}:</span>
            <span>{{ ds.cron_expression || $t('sync.no_schedule') }}</span>
          </div>
        </div>
        <div class="card-actions">
          <el-button size="small" type="primary" @click="handleSync(ds)">
            {{ $t('sync.execute') }}
          </el-button>
          <el-button size="small" @click="handleEdit(ds)">
            {{ $t('sync.edit') }}
          </el-button>
          <el-button size="small" @click="handleViewLogs(ds)">
            {{ $t('sync.log') }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(ds)">
            {{ $t('sync.delete') }}
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- Create/Edit dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('sync.edit') : $t('sync.create')"
      width="680px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="120px">
        <el-form-item :label="$t('sync.name')" prop="name">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item :label="$t('sync.workspace')" prop="oid">
          <el-select v-model="formData.oid" :placeholder="$t('sync.workspace_placeholder')">
            <el-option
              v-for="ws in workspaceOptions"
              :key="ws.id"
              :label="ws.name"
              :value="ws.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('sync.db_type')" prop="db_type">
          <el-select v-model="formData.db_type" :disabled="isEdit">
            <el-option label="MySQL" value="mysql" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('sync.host')" prop="host">
          <el-input v-model="formData.host" />
        </el-form-item>
        <el-form-item :label="$t('sync.port')" prop="port">
          <el-input-number v-model="formData.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item :label="$t('sync.username')" prop="username">
          <el-input v-model="formData.username" />
        </el-form-item>
        <el-form-item :label="$t('sync.password')" prop="password">
          <el-input v-model="formData.password" type="password" show-password />
        </el-form-item>
        <el-form-item :label="$t('sync.database')" prop="database">
          <el-input v-model="formData.database" />
        </el-form-item>
        <el-form-item :label="$t('sync.db_schema')">
          <el-input v-model="formData.db_schema" :placeholder="$t('sync.db_schema_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('sync.enabled')">
          <el-switch v-model="formData.enabled" />
        </el-form-item>

        <!-- Connection test -->
        <el-form-item>
          <el-button @click="handleTestInDialog" :loading="testLoading">
            {{ $t('sync.test_connection') }}
          </el-button>
          <span v-if="testResult !== null" :style="{ color: testResult ? '#67c23a' : '#f56c6c' }">
            {{ testResult ? $t('sync.connection_success') : $t('sync.connection_failed') }}
          </span>
        </el-form-item>

        <!-- Table mapping -->
        <el-divider>{{ $t('sync.table_mapping') }}</el-divider>
        <div v-for="mapping in mappings" :key="mapping.entity_type" class="mapping-row">
          <span class="mapping-label">{{ getEntityLabel(mapping.entity_type) }}</span>
          <el-input
            v-model="mapping.table_name"
            :placeholder="$t('sync.table_name_placeholder')"
            style="flex: 1"
          />
          <el-switch v-model="mapping.enabled" />
        </div>

        <!-- Cron schedule -->
        <el-divider>{{ $t('sync.schedule') }}</el-divider>
        <el-form-item :label="$t('sync.cron_preset')">
          <el-select v-model="cronPreset" @change="onCronPresetChange" clearable style="width: 200px">
            <el-option :label="$t('sync.every_30min')" value="*/30 * * * *" />
            <el-option :label="$t('sync.every_1hour')" value="0 * * * *" />
            <el-option :label="$t('sync.every_day')" value="0 0 * * *" />
            <el-option :label="$t('sync.custom')" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('sync.cron_expression')">
          <el-input v-model="formData.cron_expression" :disabled="cronPreset !== 'custom' && cronPreset !== ''" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- Sync result dialog -->
    <el-dialog v-model="syncResultVisible" :title="$t('sync.sync_result')" width="480px">
      <div v-if="syncSummary" class="sync-result">
        <el-descriptions :column="1" border>
          <el-descriptions-item :label="$t('sync.created')">{{ syncSummary.created || 0 }}</el-descriptions-item>
          <el-descriptions-item :label="$t('sync.updated')">{{ syncSummary.updated || 0 }}</el-descriptions-item>
          <el-descriptions-item :label="$t('sync.deactivated')">{{ syncSummary.deactivated || 0 }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- Log drawer -->
    <el-drawer v-model="logDrawerVisible" :title="$t('sync.log')" size="60%">
      <el-table :data="logItems" v-loading="logLoading">
        <el-table-column :label="$t('sync.start_time')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('sync.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('sync.summary')" min-width="200">
          <template #default="{ row }">
            <span v-if="row.summary">
              {{ formatSummary(row.summary) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('sync.error_message')" min-width="200" prop="error_message" />
      </el-table>
      <el-pagination
        v-model:current-page="logPage"
        :page-size="10"
        :total="logTotal"
        layout="total, prev, pager, next"
        @current-change="loadLogs"
        style="margin-top: 16px"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import { useI18n } from 'vue-i18n'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import {
  syncApi,
  type SyncDatasource,
  type SyncTableMapping,
  type SyncTableMappingUpdate,
  type SyncSummary,
} from '@/api/sync'
import { userApi } from '@/api/auth'

const { t } = useI18n()

// ── State ──────────────────────────────────────────────────────
const loading = ref(false)
const datasources = ref<SyncDatasource[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const testLoading = ref(false)
const testResult = ref<boolean | null>(null)
const mappings = ref<SyncTableMapping[]>([])
const cronPreset = ref('')

const formData = reactive({
  id: 0,
  name: '',
  db_type: 'mysql',
  host: '',
  port: 3306,
  username: '',
  password: '',
  database: '',
  db_schema: '',
  enabled: true,
  cron_expression: '',
  oid: 1,
})

const formRules = {
  name: [{ required: true, message: 'Required', trigger: 'blur' }],
  host: [{ required: true, message: 'Required', trigger: 'blur' }],
  port: [{ required: true, message: 'Required', trigger: 'blur' }],
  username: [{ required: true, message: 'Required', trigger: 'blur' }],
  password: [{ required: true, message: 'Required', trigger: 'blur' }],
  database: [{ required: true, message: 'Required', trigger: 'blur' }],
}

// Sync result
const syncResultVisible = ref(false)
const syncSummary = ref<SyncSummary | null>(null)

// Log drawer
const logDrawerVisible = ref(false)
const logItems = ref<any[]>([])
const logLoading = ref(false)
const logPage = ref(1)
const logTotal = ref(0)
const logDsId = ref(0)

// Workspace options
const workspaceOptions = ref<any[]>([])

// ── Helpers ────────────────────────────────────────────────────
const ENTITY_LABELS: Record<string, string> = {
  user: 'User (id, name, email, account)',
  department: 'Department (code, name, parent_code)',
  role: 'Role (code, name)',
  user_dept: 'User-Dept (user_id, dept_code, is_primary)',
  user_role: 'User-Role (user_id, role_code)',
}

function getEntityLabel(entityType: string): string {
  return ENTITY_LABELS[entityType] || entityType
}

function formatTime(ts: number): string {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

function formatSummary(summary: Record<string, number>): string {
  return Object.entries(summary)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ')
}

function resetForm() {
  formData.id = 0
  formData.name = ''
  formData.db_type = 'mysql'
  formData.host = ''
  formData.port = 3306
  formData.username = ''
  formData.password = ''
  formData.database = ''
  formData.db_schema = ''
  formData.enabled = true
  formData.cron_expression = ''
  formData.oid = 1
  mappings.value = []
  cronPreset.value = ''
  testResult.value = null
}

function getWorkspaceName(oid: any): string {
  const ws = workspaceOptions.value.find((w: any) => String(w.id) === String(oid))
  return ws ? ws.name : String(oid)
}

function onCronPresetChange(val: string) {
  if (val && val !== 'custom') {
    formData.cron_expression = val
  }
}

// ── Data loading ───────────────────────────────────────────────
async function loadDatasources() {
  loading.value = true
  try {
    const result = await syncApi.listDatasources()
    datasources.value = Array.isArray(result) ? result : []
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load datasources')
  } finally {
    loading.value = false
  }
}

// Canonical order for table mapping entity types
const ENTITY_ORDER = ['user', 'department', 'role', 'user_dept', 'user_role']

function sortMappings(ms: SyncTableMapping[]): SyncTableMapping[] {
  return [...ms].sort(
    (a, b) => ENTITY_ORDER.indexOf(a.entity_type) - ENTITY_ORDER.indexOf(b.entity_type),
  )
}

// ── Actions ────────────────────────────────────────────────────
function handleCreate() {
  resetForm()
  isEdit.value = false
  // Create default mappings in canonical order
  mappings.value = ENTITY_ORDER.map(
    (et) => ({ id: 0, ds_id: 0, entity_type: et, table_name: '', enabled: true }) as SyncTableMapping,
  )
  dialogVisible.value = true
}

async function handleEdit(ds: SyncDatasource) {
  resetForm()
  isEdit.value = true
  Object.assign(formData, {
    id: ds.id,
    name: ds.name,
    db_type: ds.db_type,
    host: ds.host,
    port: ds.port,
    username: ds.username,
    password: '',
    database: ds.database,
    db_schema: ds.db_schema || '',
    enabled: ds.enabled,
    cron_expression: ds.cron_expression,
    oid: ds.oid,
  })

  // Load mappings
  try {
    const result = await syncApi.getMappings(ds.id)
    mappings.value = sortMappings(Array.isArray(result) ? result : [])
  } catch {
    mappings.value = []
  }

  dialogVisible.value = true
}

async function handleDelete(ds: SyncDatasource) {
  try {
    await ElMessageBox.confirm(
      t('sync.delete_confirm', { name: ds.name }),
      t('sync.delete'),
      { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' },
    )
    await syncApi.deleteDatasource(ds.id)
    ElMessage.success(t('sync.delete_success'))
    await loadDatasources()
  } catch {
    // cancelled or error
  }
}

async function handleTestConnection(ds: SyncDatasource) {
  try {
    const result = await syncApi.testConnection(ds.id)
    if (result?.success) {
      ElMessage.success(t('sync.connection_success'))
    } else {
      ElMessage.error(result?.message || t('sync.connection_failed'))
    }
  } catch (e: any) {
    ElMessage.error(e.message || t('sync.connection_failed'))
  }
}

async function handleTestInDialog() {
  // For new datasources, save first then test
  if (!isEdit.value && !formData.id) {
    ElMessage.warning(t('sync.save_first_to_test'))
    return
  }
  testLoading.value = true
  try {
    const result = await syncApi.testConnection(formData.id)
    testResult.value = result?.success ?? false
    if (testResult.value) {
      ElMessage.success(t('sync.connection_success'))
    } else {
      ElMessage.error(result?.message || t('sync.connection_failed'))
    }
  } catch {
    testResult.value = false
  } finally {
    testLoading.value = false
  }
}

async function handleSync(ds: SyncDatasource) {
  try {
    await ElMessageBox.confirm(
      t('sync.execute_confirm', { name: ds.name }),
      t('sync.execute'),
      { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'info' },
    )
    const result = await syncApi.executeSync(ds.id)
    if (result?.success) {
      syncSummary.value = result.summary
      syncResultVisible.value = true
      ElMessage.success(t('sync.sync_success'))
    } else {
      ElMessage.error(t('sync.sync_failed'))
    }
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.message || t('sync.sync_failed'))
    }
  }
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      const updateData: any = { id: formData.id }
      if (formData.name) updateData.name = formData.name
      if (formData.host) updateData.host = formData.host
      if (formData.port) updateData.port = formData.port
      if (formData.username) updateData.username = formData.username
      if (formData.password) updateData.password = formData.password
      if (formData.database) updateData.database = formData.database
      updateData.db_schema = formData.db_schema
      updateData.enabled = formData.enabled
      updateData.cron_expression = formData.cron_expression
      updateData.oid = formData.oid

      await syncApi.updateDatasource(updateData)

      // Save mappings
      const mappingUpdates: SyncTableMappingUpdate[] = mappings.value.map((m) => ({
        entity_type: m.entity_type,
        table_name: m.table_name,
        enabled: m.enabled,
      }))
      await syncApi.updateMappings(formData.id, mappingUpdates)

      // Update schedule
      if (formData.cron_expression) {
        await syncApi.updateSchedule(formData.id, formData.cron_expression)
      }
    } else {
      const result = await syncApi.createDatasource({
        name: formData.name,
        db_type: formData.db_type,
        host: formData.host,
        port: formData.port,
        username: formData.username,
        password: formData.password,
        database: formData.database,
        db_schema: formData.db_schema || null,
        enabled: formData.enabled,
        cron_expression: formData.cron_expression,
        oid: formData.oid,
      })

      // Save mappings for newly created datasource
      if (result?.id) {
        const mappingUpdates: SyncTableMappingUpdate[] = mappings.value.map((m) => ({
          entity_type: m.entity_type,
          table_name: m.table_name,
          enabled: m.enabled,
        }))
        await syncApi.updateMappings(result.id, mappingUpdates)
      }
    }

    ElMessage.success(t('sync.save_success'))
    dialogVisible.value = false
    await loadDatasources()
  } catch (e: any) {
    ElMessage.error(e.message || t('sync.save_failed'))
  } finally {
    saving.value = false
  }
}

async function handleViewLogs(ds: SyncDatasource) {
  logDsId.value = ds.id
  logPage.value = 1
  logDrawerVisible.value = true
  await loadLogs()
}

async function loadLogs() {
  logLoading.value = true
  try {
    const result = await syncApi.getLogs(logDsId.value, logPage.value, 10)
    logItems.value = result?.items || []
    logTotal.value = result?.total || 0
  } catch {
    logItems.value = []
  } finally {
    logLoading.value = false
  }
}

// ── Init ───────────────────────────────────────────────────────
onMounted(async () => {
  loadDatasources()
  // Load workspace options
  try {
    const result = await userApi.ws_options()
    workspaceOptions.value = Array.isArray(result) ? result : []
  } catch {
    workspaceOptions.value = []
  }
})
</script>

<style scoped lang="less">
.sync-container {
  padding: 20px;
}

.tool-left {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  .page-title {
    font-weight: 500;
    font-size: 20px;
    line-height: 28px;
  }
}

.sync-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
}

.sync-card {
  width: 400px;
  min-width: 360px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .ds-name {
      font-weight: 600;
      font-size: 16px;
    }
  }

  .card-body {
    .card-info {
      margin-bottom: 6px;
      font-size: 13px;

      .info-label {
        color: var(--el-text-color-secondary);
        margin-right: 8px;
        min-width: 80px;
        display: inline-block;
      }
    }
  }

  .card-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
  }
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;

  .mapping-label {
    min-width: 240px;
    font-size: 13px;
    color: var(--el-text-color-regular);
  }
}

.sync-result {
  padding: 16px 0;
}
</style>

<style lang="less">
.sync-card .card-actions .el-button {
  margin-left: 0 !important;
}
</style>
