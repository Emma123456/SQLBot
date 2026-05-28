<template>
  <div class="select-dept_permission">
    <p class="lighter-bold">{{ $t('permission.select_restricted_dept') }}</p>
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
        <div class="mt-8 max-height_workspace" style="margin-left: 16px">
          <el-tree
            ref="treeRef"
            :data="deptTree"
            :props="{ label: 'name', children: 'children' }"
            show-checkbox
            node-key="id"
            :filter-node-method="filterNode"
            :default-checked-keys="selectedKeys"
            @check="handleCheck"
          />
        </div>
      </div>
      <div class="p-16 w-full">
        <div class="flex-between mb-16" style="margin: 0 16px">
          <span class="lighter">
            {{ $t('permission.selected_depts', { msg: checkedTableList.length }) }}
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
              <icon_dept></icon_dept>
            </el-icon>
            <span class="ml-4 lighter ellipsis" style="max-width: 80%" :title="ele.name">{{
              ele.name
            }}</span>
          </div>
          <el-button class="close-btn" text>
            <el-icon size="16" @click="removeDept(ele)"><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'
import { departmentApi } from '@/api/department'
import icon_dept from '@/assets/svg/icon_member_outlined.svg'
import Close from '@/assets/svg/icon_close_outlined_w.svg'
import Search from '@/assets/svg/icon_search-outline_outlined.svg'
import type { DepartmentTreeNode } from '@/api/department'
import { useUserStore } from '@/stores/user'

const search = ref('')
const loading = ref(false)
const deptTree = ref<DepartmentTreeNode[]>([])
const checkedTableList = ref<any[]>([])
const selectedKeys = ref<any[]>([])
const treeRef = ref()
const userStore = useUserStore()

watch(search, (val) => {
  treeRef.value?.filter(val)
})

const filterNode = (value: string, data: any) => {
  if (!value) return true
  return data.name.includes(value)
}

const handleCheck = () => {
  if (!treeRef.value) return
  const checkedNodes = treeRef.value.getCheckedNodes(false, true) as any[]
  checkedTableList.value = checkedNodes.map((node: any) => ({
    id: node.id,
    name: node.name,
  }))
}

const flatTree = (nodes: DepartmentTreeNode[]): any[] => {
  const result: any[] = []
  for (const node of nodes) {
    result.push({ id: node.id, name: node.name })
    if (node.children?.length) {
      result.push(...flatTree(node.children))
    }
  }
  return result
}

const open = async (selectedIds: any[]) => {
  loading.value = true
  search.value = ''
  checkedTableList.value = []
  selectedKeys.value = selectedIds || []
  try {
    const currentOid = userStore.getOid ? Number(userStore.getOid) : undefined
    const res = await departmentApi.tree(undefined, currentOid)
    deptTree.value = res || []
    // Pre-populate checkedTableList from selectedIds
    if (selectedIds?.length) {
      const allNodes = flatTree(deptTree.value)
      // Normalize IDs to strings for comparison (large IDs are strings via json-bigint storeAsString)
      const idSet = new Set(selectedIds.map(String))
      checkedTableList.value = allNodes.filter((n) => idSet.has(String(n.id)))
    }
  } finally {
    loading.value = false
  }
}

const removeDept = (val: any) => {
  treeRef.value?.setChecked(val.id, false, false)
  checkedTableList.value = checkedTableList.value.filter((ele: any) => String(ele.id) !== String(val.id))
}

const clearAll = () => {
  treeRef.value?.setCheckedKeys([])
  checkedTableList.value = []
}

defineExpose({
  open,
  checkedTableList,
})
</script>

<style lang="less">
.select-dept_permission {
  .lighter-bold {
    margin-bottom: 16px;
    font-weight: 500;
    font-size: 16px;
    line-height: 24px;
  }

  .p-16 {
    padding: 16px 0;
  }

  .lighter {
    font-weight: 400;
    font-size: 14px;
    line-height: 22px;
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

  .hover-bg_select {
    &:hover {
      &::after {
        content: '';
        height: 44px;
        width: calc(100% + 16px);
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
}
</style>
