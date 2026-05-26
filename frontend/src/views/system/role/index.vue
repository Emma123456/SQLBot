<template>
  <div class="sqlbot-table-container role-container">
    <div class="tool-left">
      <span class="page-title">{{ $t('role.management') }}</span>
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          :placeholder="$t('role.search_placeholder')"
          clearable
          style="width: 240px; margin-right: 12px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" @click="handleCreate()">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('role.create') }}
        </el-button>
      </div>
    </div>

    <el-table :data="tableData" style="width: 100%" v-loading="loading">
      <el-table-column prop="name" :label="$t('role.name')" min-width="140" />
      <el-table-column prop="code" :label="$t('role.code')" min-width="140" />
      <el-table-column prop="description" :label="$t('role.description')" min-width="200" show-overflow-tooltip />
      <el-table-column :label="$t('role.users')" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleManageUsers(row)">
            {{ $t('role.manageUsers') }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column :label="$t('ds.actions')" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">
            {{ $t('datasource.edit') }}
          </el-button>
          <el-button link type="danger" @click="handleDelete(row)">
            {{ $t('dashboard.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrapper" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadRoles"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? $t('role.edit') : $t('role.create')"
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
        <el-form-item :label="$t('role.name')" prop="name">
          <el-input
            v-model="formData.name"
            :placeholder="$t('datasource.please_enter') + $t('role.name')"
            maxlength="128"
            clearable
          />
        </el-form-item>
        <el-form-item :label="$t('role.code')" prop="code">
          <el-input
            v-model="formData.code"
            :placeholder="$t('datasource.please_enter') + $t('role.code')"
            maxlength="128"
            :disabled="isEdit"
            clearable
          />
        </el-form-item>
        <el-form-item :label="$t('role.description')" prop="description">
          <el-input
            v-model="formData.description"
            :placeholder="$t('datasource.please_enter') + $t('role.description')"
            type="textarea"
            maxlength="512"
            :rows="3"
            clearable
          />
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
      :title="$t('role.manageUsers') + ' - ' + currentRole?.name"
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

        <el-table :data="roleUsers" style="width: 100%" v-loading="usersLoading">
          <el-table-column prop="name" :label="$t('user.name')" />
          <el-table-column prop="account" :label="$t('user.account')" />
          <el-table-column prop="email" :label="$t('user.email')" />
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
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { roleApi, type Role } from '@/api/role'
import { userApi } from '@/api/user'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'

const { t } = useI18n()

const formRef = ref()
const loading = ref(false)
const submitLoading = ref(false)
const usersLoading = ref(false)
const tableData = ref<Role[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')

// Dialog state
const dialogVisible = ref(false)
const isEdit = ref(false)
const formData = reactive({
  id: 0,
  name: '',
  code: '',
  description: '',
})

// Drawer state
const drawerVisible = ref(false)
const currentRole = ref<Role | null>(null)
const roleUsers = ref<any[]>([])
const allUsers = ref<any[]>([])
const selectedUserIds = ref<number[]>([])

const formRules = {
  name: [{ required: true, message: t('datasource.please_enter') + t('role.name'), trigger: 'blur' }],
  code: [{ required: true, message: t('datasource.please_enter') + t('role.code'), trigger: 'blur' }],
}

const loadRoles = async () => {
  loading.value = true
  try {
    const res = await roleApi.list(currentPage.value, pageSize.value, searchKeyword.value || undefined)
    tableData.value = res?.items || []
    total.value = res?.total || 0
  } catch (e) {
    console.error('Failed to load roles:', e)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadRoles()
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadRoles()
}

const handleCreate = () => {
  isEdit.value = false
  formData.id = 0
  formData.name = ''
  formData.code = ''
  formData.description = ''
  dialogVisible.value = true
}

const handleEdit = (row: Role) => {
  isEdit.value = true
  formData.id = row.id
  formData.name = row.name
  formData.code = row.code
  formData.description = row.description || ''
  dialogVisible.value = true
}

const handleDelete = async (row: Role) => {
  try {
    await ElMessageBox.confirm(t('role.delete_confirm', { name: row.name }), {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    })
    await roleApi.delete(row.id)
    ElMessage.success(t('dashboard.delete_success'))
    loadRoles()
  } catch (e: any) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    } else if (e !== 'cancel') {
      console.error('Failed to delete role:', e)
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
      await roleApi.update({
        id: formData.id,
        name: formData.name,
        code: formData.code,
        description: formData.description || null,
      })
    } else {
      await roleApi.create({
        name: formData.name,
        code: formData.code,
        description: formData.description || null,
      })
    }
    ElMessage.success(t('common.save_success'))
    onDialogClose()
    loadRoles()
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
  formData.description = ''
}

const handleManageUsers = async (row: Role) => {
  currentRole.value = row
  drawerVisible.value = true
  await loadRoleUsers(row.id)
  await loadAllUsers()
}

const loadRoleUsers = async (roleId: number) => {
  usersLoading.value = true
  try {
    const res = await roleApi.getUsers(roleId)
    roleUsers.value = res || []
  } catch (e) {
    console.error('Failed to load role users:', e)
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
  if (!currentRole.value || !selectedUserIds.value.length) return
  try {
    await roleApi.assignUsers(currentRole.value.id, selectedUserIds.value)
    ElMessage.success(t('common.save_success'))
    selectedUserIds.value = []
    loadRoleUsers(currentRole.value.id)
  } catch (e: any) {
    if (e?.response?.data?.detail) {
      ElMessage.error(e.response.data.detail)
    }
  }
}

const handleRemoveUser = async (user: any) => {
  if (!currentRole.value) return
  try {
    await ElMessageBox.confirm(t('role.remove_user_confirm', { name: user.name }), {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    })
    await roleApi.removeUsers(currentRole.value.id, [user.id])
    ElMessage.success(t('dashboard.delete_success'))
    loadRoleUsers(currentRole.value.id)
  } catch (e: any) {
    if (e !== 'cancel') {
      if (e?.response?.data?.detail) {
        ElMessage.error(e.response.data.detail)
      }
    }
  }
}

onMounted(() => {
  loadRoles()
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

    .search-bar {
      display: flex;
      align-items: center;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}

.action-btn-danger {
  cursor: pointer;
  color: #646a73;
  &:hover {
    color: var(--ed-color-danger);
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
