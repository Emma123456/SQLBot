<template>
  <div class="select-role_permission">
    <p class="lighter-bold">{{ $t('permission.select_restricted_role') }}</p>
    <div v-loading="loading" class="flex border" style="height: 428px; border-radius: 6px">
      <div class="p-16 border-r">
        <el-input
          v-model="search"
          :validate-event="false"
          :placeholder="$t('datasource.search')"
          style="width: 364px; margin-left: 16px"
          clearable
        >
          <template #prefix>
            <el-icon>
              <Search></Search>
            </el-icon>
          </template>
        </el-input>
        <div class="mt-8 max-height_workspace">
          <el-checkbox
            v-model="checkAll"
            class="mb-8"
            style="margin-left: 16px"
            :indeterminate="isIndeterminate"
            @change="handleCheckAllChange"
          >
            {{ $t('datasource.select_all') }}
          </el-checkbox>
          <el-checkbox-group
            v-model="checkedRoleIds"
            class="checkbox-group-block"
            @change="handleCheckedRolesChange"
          >
            <el-checkbox
              v-for="role in rolesWithKeywords"
              :key="role.id"
              :label="role.name"
              :value="role.id"
              class="hover-bg"
            >
              <div class="flex">
                <el-icon size="28">
                  <icon_member></icon_member>
                </el-icon>
                <span class="ml-4 ellipsis" style="max-width: 80%" :title="role.name">
                  {{ role.name }}</span
                >
              </div>
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </div>
      <div class="p-16 w-full">
        <div class="flex-between mb-16" style="margin: 0 16px">
          <span class="lighter">
            {{ $t('permission.selected_roles', { msg: checkedTableList.length }) }}
          </span>

          <el-button text @click="clearAll">
            {{ $t('workspace.clear') }}
          </el-button>
        </div>
        <div
          v-for="ele in checkedTableList"
          :key="ele.id"
          style="margin: 0 16px; position: relative"
          class="flex-between align-center hover-bg_select"
        >
          <div class="flex align-center ellipsis" style="width: 100%">
            <el-icon size="28">
              <icon_member></icon_member>
            </el-icon>
            <span class="ml-4 lighter ellipsis" style="max-width: 80%" :title="ele.name">{{
              ele.name
            }}</span>
          </div>
          <el-button class="close-btn" text>
            <el-icon size="16" @click="removeRole(ele)"><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue'
import { roleApi } from '@/api/role'
import icon_member from '@/assets/svg/icon_member_outlined.svg'
import Close from '@/assets/svg/icon_close_outlined_w.svg'
import Search from '@/assets/svg/icon_search-outline_outlined.svg'
import type { CheckboxValueType } from 'element-plus-secondary'
import { useUserStore } from '@/stores/user'

const checkAll = ref(false)
const isIndeterminate = ref(false)
const checkedRoleIds = ref<any[]>([])
const roles = ref<any[]>([])
const search = ref('')
const loading = ref(false)
const checkedTableList = ref<any[]>([])
const userStore = useUserStore()

const rolesWithKeywords = computed(() => {
  return roles.value.filter((ele: any) => (ele.name as string).includes(search.value))
})

watch(search, () => {
  // Normalize to strings for comparison (large IDs are strings via json-bigint storeAsString)
  const idArr = rolesWithKeywords.value.map((ele: any) => String(ele.id))
  const visibleCheckedCount = checkedRoleIds.value.filter((id) => idArr.includes(String(id))).length
  checkAll.value = visibleCheckedCount === rolesWithKeywords.value.length && rolesWithKeywords.value.length > 0
  isIndeterminate.value = visibleCheckedCount > 0 && visibleCheckedCount < rolesWithKeywords.value.length
})

const handleCheckAllChange = (val: CheckboxValueType) => {
  const visibleIds = rolesWithKeywords.value.map((ele: any) => ele.id)
  if (val) {
    // Add all visible IDs (use String comparison for dedup)
    const existingStr = new Set(checkedRoleIds.value.map(String))
    checkedRoleIds.value = [...checkedRoleIds.value, ...visibleIds.filter((id: any) => !existingStr.has(String(id)))]
  } else {
    // Remove all visible IDs
    const removeStr = new Set(visibleIds.map(String))
    checkedRoleIds.value = checkedRoleIds.value.filter((id) => !removeStr.has(String(id)))
  }
  isIndeterminate.value = false
  syncCheckedTableList()
}

const syncCheckedTableList = () => {
  // Normalize IDs to strings for comparison (handles BigInt vs Number mismatch)
  const idSet = new Set(checkedRoleIds.value.map(String))
  checkedTableList.value = roles.value.filter((ele: any) => idSet.has(String(ele.id)))
}

const handleCheckedRolesChange = () => {
  const visibleIds = new Set(rolesWithKeywords.value.map((ele: any) => String(ele.id)))
  const visibleCheckedCount = checkedRoleIds.value.filter((id) => visibleIds.has(String(id))).length
  checkAll.value = visibleCheckedCount === rolesWithKeywords.value.length && rolesWithKeywords.value.length > 0
  isIndeterminate.value = visibleCheckedCount > 0 && visibleCheckedCount < rolesWithKeywords.value.length
  syncCheckedTableList()
}

const open = async (selectedIds: number[]) => {
  loading.value = true
  search.value = ''
  checkedRoleIds.value = []
  checkAll.value = false
  checkedTableList.value = []
  isIndeterminate.value = false
  try {
    const currentOid = userStore.getOid ? Number(userStore.getOid) : undefined
    const res = await roleApi.all(currentOid)
    roles.value = res || []
    if (selectedIds?.length) {
      checkedRoleIds.value = [...selectedIds]
      syncCheckedTableList()
    }
  } finally {
    loading.value = false
  }
}

const removeRole = (val: any) => {
  checkedRoleIds.value = checkedRoleIds.value.filter((id) => String(id) !== String(val.id))
  syncCheckedTableList()
  handleCheckedRolesChange()
}

const clearAll = () => {
  checkedRoleIds.value = []
  syncCheckedTableList()
}

defineExpose({
  open,
  checkedTableList,
})
</script>

<style lang="less">
.select-role_permission {
  .lighter-bold {
    margin-bottom: 16px;
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
  }

  .mb-8 {
    margin-bottom: 8px;
  }

  .ed-checkbox {
    margin-right: 0;
    position: relative;
  }

  .hover-bg,
  .hover-bg_select {
    &:hover {
      &::after {
        content: '';
        height: 44px;
        width: calc(100% + 34px);
        background: #1f23291a;
        position: absolute;
        border-radius: 6px;
        top: 50%;
        transform: translateY(-50%);
        left: -8px;
        z-index: 1;
      }
    }
  }

  .hover-bg_select {
    &:hover {
      &::after {
        width: calc(100% + 16px);
      }
    }
  }

  .p-16 {
    padding: 16px 0;
  }

  .lighter {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
  }

  .checkbox-group-block {
    margin: 0 16px;
  }

  .checkbox-group-block {
    .ed-checkbox,
    .ed-checkbox__label,
    .flex {
      width: 96%;
      height: 44px;
    }

    .flex {
      align-items: center;
    }
  }

  .close-btn {
    position: relative;
    z-index: 10;
    height: 24px;
    line-height: 24px;
    &:hover,
    &:active,
    &:focus {
      background: #1f23291a !important;
    }
  }

  .border {
    border: 1px solid #dee0e3;
  }

  .w-full {
    height: 100%;
    width: 50%;
    overflow-y: auto;

    .flex-between {
      height: 44px;
    }
  }

  .mt-8 {
    margin-top: 8px;
  }

  .max-height_workspace {
    max-height: calc(100% - 24px);
    overflow-y: auto;
  }

  .align-center {
    align-items: center;
  }

  .flex-between {
    display: flex;
    justify-content: space-between;
  }

  .ml-4 {
    margin-left: 4px;
  }

  .flex {
    display: flex;
  }

  .border-r {
    border-right: 1px solid #dee0e3;
    width: 50%;
    overflow: hidden;
  }
}
</style>
