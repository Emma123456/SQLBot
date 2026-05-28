<template>
  <div class="sqlbot-table-container department-container">
    <div class="tool-left">
      <span class="page-title">{{ $t('department.management') }}</span>
      <div class="search-bar">
        <el-select
          v-model="filterOid"
          :placeholder="$t('department.workspace_placeholder')"
          clearable
          style="width: 180px; margin-right: 12px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="ws in workspaceOptions"
            :key="ws.id"
            :label="ws.name"
            :value="ws.id"
          />
        </el-select>
        <el-select
          v-model="filterDsId"
          :placeholder="$t('department.sync_datasource_placeholder')"
          clearable
          style="width: 180px; margin-right: 12px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="ds in syncDsOptions"
            :key="ds.id"
            :label="ds.name"
            :value="ds.id"
          />
        </el-select>
        <el-button type="primary" @click="handleCreate()">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('department.create') }}
        </el-button>
      </div>
    </div>

    <div class="department-tree-wrapper">
      <el-tree
        ref="treeRef"
        :data="treeData"
        node-key="id"
        :props="treeProps"
        default-expand-all
        :expand-on-click-node="false"
        highlight-current
      >
        <template #default="{ data }">
          <div class="tree-node">
            <span class="node-label">{{ data.name }}</span>
            <span class="node-code">{{ data.code }}</span>
            <span class="node-workspace" v-if="data.oid">{{ getWorkspaceName(data.oid) }}</span>
            <div class="node-actions">
              <el-tooltip effect="dark" :content="$t('department.create')" placement="top">
                <el-icon class="action-btn" size="14" @click.stop="handleCreate(data)">
                  <icon_add_outlined />
                </el-icon>
              </el-tooltip>
              <el-tooltip effect="dark" :content="$t('datasource.edit')" placement="top">
                <el-icon class="action-btn" size="14" @click.stop="handleEdit(data)">
                  <IconOpeEdit />
                </el-icon>
              </el-tooltip>
              <el-tooltip effect="dark" :content="$t('department.manageUsers')" placement="top">
                <el-icon class="action-btn" size="14" @click.stop="handleManageUsers(data)">
                  <icon_user_outlined />
                </el-icon>
              </el-tooltip>
              <el-tooltip effect="dark" :content="$t('dashboard.delete')" placement="top">
                <el-icon class="action-btn action-btn-danger" size="14" @click.stop="handleDelete(data)">
                  <IconOpeDelete />
                </el-icon>
              </el-tooltip>
            </div>
          </div>
        </template>
      </el-tree>
      <el-empty v-if="!treeData.length && !loading" :description="$t('department.no_departments')" />
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('department.edit') : $t('department.create')"
      width="480px"
      destroy-on-close
      :before-close="onDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        label-position="top"
        @submit.prevent
      >
        <el-form-item :label="$t('department.name')" prop="name">
          <el-input
            v-model="formData.name"
            :placeholder="$t('datasource.please_enter') + $t('department.name')"
            maxlength="128"
            clearable
          />
        </el-form-item>
        <el-form-item :label="$t('department.code')" prop="code">
          <el-input
            v-model="formData.code"
            :placeholder="$t('datasource.please_enter') + $t('department.code')"
            maxlength="128"
            :disabled="isEdit"
            clearable
          />
        </el-form-item>
        <el-form-item :label="$t('department.parent')" prop="parent_id">
          <el-tree-select
            v-model="formData.parent_id"
            :data="parentTreeOptions"
            :props="{ children: 'children', label: 'name', value: 'id' }"
            :placeholder="$t('department.root')"
            clearable
            check-strictly
            :render-after-expand="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="$t('department.workspace')" prop="oid">
          <el-select
            v-model="formData.oid"
            :placeholder="$t('department.workspace_placeholder')"
            style="width: 100%"
          >
            <el-option
              v-for="ws in workspaceOptions"
              :key="ws.id"
              :label="ws.name"
              :value="ws.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button secondary @click="onDialogClose">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
            {{ $t('common.save') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- User Management Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="$t('department.manageUsers') + ' - ' + currentDept?.name"
      size="520px"
      destroy-on-close
    >
      <div class="drawer-content">
        <div class="drawer-toolbar">
          <el-select
            v-model="selectedUserIds"
            multiple
            filterable
            :placeholder="$t('datasource.Please_select') + $t('user.user_management')"
            style="width: 100%"
          >
            <el-option
              v-for="user in allUsers"
              :key="user.id"
              :label="`${user.name} (${user.account})`"
              :value="user.id"
            />
          </el-select>
          <el-button type="primary" size="small" @click="handleAddUsers" :disabled="!selectedUserIds.length">
            {{ $t('model.add') }}
          </el-button>
        </div>

        <el-table :data="deptUsers" style="width: 100%" v-loading="usersLoading">
          <el-table-column prop="name" :label="$t('user.name')" />
          <el-table-column prop="account" :label="$t('user.account')" />
          <el-table-column prop="is_primary" :label="$t('department.is_primary')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_primary ? 'primary' : 'info'" size="small">
                {{ row.is_primary ? $t('common.yes') : $t('common.no') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('ds.actions')" width="80">
            <template #default="{ row }">
              <el-icon class="action-btn action-btn-danger" size="14" @click="handleRemoveUser(row)">
                <IconOpeDelete />
              </el-icon>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { departmentApi, type DepartmentTreeNode } from '@/api/department'
import { userApi } from '@/api/user'
import { syncApi } from '@/api/sync'
import { workspaceList } from '@/api/workspace'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_user_outlined from '@/assets/svg/icon_user.svg'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'

const { t } = useI18n()

const treeRef = ref()
const formRef = ref()
const loading = ref(false)
const submitLoading = ref(false)
const usersLoading = ref(false)
const treeData = ref<DepartmentTreeNode[]>([])
const filterOid = ref<number | undefined>(undefined)
const filterDsId = ref<number | undefined>(undefined)
const workspaceOptions = ref<any[]>([])
const syncDsOptions = ref<any[]>([])

// Dialog state
const dialogVisible = ref(false)
const isEdit = ref(false)
const formData = reactive({
  id: 0,
  name: '',
  code: '',
  parent_id: 0,
  oid: 1 as number,
})

// Drawer state
const drawerVisible = ref(false)
const currentDept = ref<DepartmentTreeNode | null>(null)
const deptUsers = ref<any[]>([])
const allUsers = ref<any[]>([])
const selectedUserIds = ref<number[]>([])

const treeProps = {
  children: 'children',
  label: 'name',
}

const formRules = {
  name: [{ required: true, message: t('datasource.please_enter') + t('department.name'), trigger: 'blur' }],
  code: [{ required: true, message: t('datasource.please_enter') + t('department.code'), trigger: 'blur' }],
}

// Build parent tree options (exclude current node when editing to prevent circular reference)
const parentTreeOptions = computed(() => {
  if (!isEdit.value || !formData.id) return treeData.value
  // Filter out the current department and its descendants
  const filterTree = (nodes: DepartmentTreeNode[]): any[] => {
    return nodes
      .filter((n) => n.id !== formData.id)
      .map((n) => ({
        ...n,
        children: n.children ? filterTree(n.children) : [],
      }))
  }
  return filterTree(treeData.value)
})

const loadTree = async () => {
  loading.value = true
  try {
    const res = await departmentApi.tree(filterDsId.value, filterOid.value)
    treeData.value = res || []
  } catch (e) {
    console.error('Failed to load department tree:', e)
  } finally {
    loading.value = false
  }
}

const handleCreate = (parentData?: DepartmentTreeNode) => {
  isEdit.value = false
  formData.id = 0
  formData.name = ''
  formData.code = ''
  formData.parent_id = parentData?.id || 0
  formData.oid = 1
  dialogVisible.value = true
}

const handleEdit = (data: DepartmentTreeNode) => {
  isEdit.value = true
  formData.id = data.id
  formData.name = data.name
  formData.code = data.code
  formData.parent_id = data.parent_id
  formData.oid = data.oid || 1
  dialogVisible.value = true
}

const handleDelete = async (data: DepartmentTreeNode) => {
  try {
    await ElMessageBox.confirm(t('department.delete_confirm', { name: data.name }), {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    })
    await departmentApi.delete(data.id)
    ElMessage.success(t('dashboard.delete_success'))
    loadTree()
  } catch (e: any) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    } else if (e !== 'cancel') {
      console.error('Failed to delete department:', e)
    }
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await departmentApi.update({
        id: formData.id,
        name: formData.name,
        code: formData.code,
        parent_id: formData.parent_id,
        oid: formData.oid,
      })
    } else {
      await departmentApi.create({
        name: formData.name,
        code: formData.code,
        parent_id: formData.parent_id || 0,
        oid: formData.oid,
      })
    }
    ElMessage.success(t('common.save_success'))
    onDialogClose()
    loadTree()
  } catch (e: any) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    }
  } finally {
    submitLoading.value = false
  }
}

const onDialogClose = () => {
  dialogVisible.value = false
  formData.id = 0
  formData.name = ''
  formData.code = ''
  formData.parent_id = 0
  formData.oid = 1
}

const getWorkspaceName = (oid: number) => {
  const ws = workspaceOptions.value.find((w: any) => String(w.id) === String(oid))
  return ws?.name || String(oid)
}

const handleFilterChange = () => {
  loadTree()
}

const handleManageUsers = async (data: DepartmentTreeNode) => {
  currentDept.value = data
  drawerVisible.value = true
  await loadDeptUsers(data.id)
  await loadAllUsers()
}

const loadDeptUsers = async (deptId: number) => {
  usersLoading.value = true
  try {
    const res = await departmentApi.getUsers(deptId)
    deptUsers.value = res || []
  } catch (e) {
    console.error('Failed to load department users:', e)
  } finally {
    usersLoading.value = false
  }
}

const loadAllUsers = async () => {
  try {
    const res = await userApi.pager('', 1, 1000)
    allUsers.value = res?.items || []
  } catch (e) {
    console.error('Failed to load users:', e)
  }
}

const handleAddUsers = async () => {
  if (!currentDept.value || !selectedUserIds.value.length) return
  try {
    await departmentApi.assignUsers(currentDept.value.id, selectedUserIds.value)
    ElMessage.success(t('common.save_success'))
    selectedUserIds.value = []
    loadDeptUsers(currentDept.value.id)
  } catch (e: any) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    }
  }
}

const handleRemoveUser = async (user: any) => {
  if (!currentDept.value) return
  try {
    await ElMessageBox.confirm(t('department.remove_user_confirm', { name: user.name }), {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    })
    await departmentApi.removeUsers(currentDept.value.id, [user.id])
    ElMessage.success(t('dashboard.delete_success'))
    loadDeptUsers(currentDept.value.id)
  } catch (e: any) {
    if (e !== 'cancel') {
      if (e?.response?.data?.detail) {
        ElMessage.error(e.response.data.detail)
      }
    }
  }
}

onMounted(() => {
  loadTree()
  // Load workspace options
  workspaceList().then((res) => {
    workspaceOptions.value = res || []
  }).catch(() => {
    workspaceOptions.value = []
  })
  // Load sync datasource options
  syncApi.listDatasources().then((res: any) => {
    syncDsOptions.value = res || []
  }).catch(() => {
    syncDsOptions.value = []
  })
})
</script>

<style lang="less" scoped>
.sqlbot-table-container {
  width: 100%;
  height: 100%;
  position: relative;

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

  .department-tree-wrapper {
    width: 100%;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    padding: 12px;
    background-color: #fff;
    border-radius: 8px;
    border: 1px solid #ebeef5;
  }
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 4px 0;

  .node-label {
    font-size: 14px;
    font-weight: 500;
  }

  .node-code {
    font-size: 12px;
    color: #909399;
    margin-left: 8px;
  }

  .node-workspace {
    font-size: 12px;
    color: #409eff;
    margin-left: 8px;
  }

  .node-actions {
    display: none;
    align-items: center;
    gap: 4px;

    .action-btn {
      width: 24px;
      height: 24px;
      border-radius: 4px;
      cursor: pointer;
      color: #646a73;
      display: flex;
      align-items: center;
      justify-content: center;

      &:hover {
        background-color: #1f23291a;
      }

      &.action-btn-danger:hover {
        color: var(--ed-color-danger);
      }
    }
  }

  &:hover .node-actions {
    display: flex;
  }
}

.drawer-content {
  .drawer-toolbar {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    align-items: center;

    .el-select {
      flex: 1;
    }
  }
}
</style>
