<script>
export const plugin = { label: 'Provider orders', icon: 'package', requires: 'POD Provider Order', order: 2 }
</script>

<script setup>
import { computed, ref, watch } from 'vue'
import { Select } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import {
  EmptyState,
  ListPagination,
  ListSkeleton,
  StatusBadge,
  shortDate,
  usePlugin,
  useMethodRead,
  usePage,
} from '@commera/admin'
import { statusKey } from '../../shared/status'

const ALL_ORDERS = 'all'
const ROW_HEIGHT = 60

const { navigate } = usePlugin()
usePage().setActions([{ label: 'Print jobs', icon: 'printer', onClick: () => navigate('jobs') }])

const status = ref(ALL_ORDERS)
const page = ref(1)
const pageSize = ref(20)

const ordersRequest = useMethodRead('commera_print_on_demand.api.get_provider_orders', {
  params: () => ({
    status: status.value === ALL_ORDERS ? undefined : status.value,
    start: (page.value - 1) * pageSize.value,
    page_length: pageSize.value,
  }),
  refetch: true,
})

watch(status, () => (page.value = 1))

const rows = computed(() => ordersRequest.data?.rows ?? [])
const total = computed(() => ordersRequest.data?.total ?? 0)

const statusOptions = computed(() => {
  const counts = ordersRequest.data?.counts ?? {}
  const allCount = Object.values(counts).reduce((sum, count) => sum + count, 0)
  return [
    { label: `All orders (${allCount})`, value: ALL_ORDERS },
    ...Object.entries(counts).map(([name, count]) => ({ label: `${name} (${count})`, value: name })),
  ]
})

const skeletonColumns = window.matchMedia('(max-width: 639.98px)').matches ? 2 : 5

function openJob(order) {
  if (order.job) navigate(`jobs/${order.job}`)
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <Select v-model="status" :options="statusOptions" />
  </div>

  <div class="mt-3 overflow-x-auto">
    <List
      class="max-sm:[--list-columns:minmax(0,1fr)_auto] sm:min-w-[44rem]"
      :row-height="ROW_HEIGHT"
      :columns="['1fr', '11rem', '5rem', '7rem', '8rem']"
    >
      <ListHeader>
        <ListHeaderCell>Provider order</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Product</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Qty</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Received</ListHeaderCell>
        <ListHeaderCell>Status</ListHeaderCell>
      </ListHeader>

      <ListSkeleton v-if="ordersRequest.loading && !rows.length" :columns="skeletonColumns" />

      <ListRows v-else :items="rows" row-key="name" v-slot="{ item }">
        <ListRow :value="item.name" @click="openJob(item)">
          <ListCell>
            <div class="min-w-0">
              <p class="truncate text-base text-ink-gray-8 tabular-nums">{{ item.name }}</p>
              <p class="truncate text-sm text-ink-gray-4 tabular-nums">{{ item.job || 'No print job' }}</p>
            </div>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="truncate text-base text-ink-gray-7">{{ item.product_id || '—' }}</span>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="text-base text-ink-gray-7 tabular-nums">{{ item.qty }}</span>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="text-base text-ink-gray-5">{{ shortDate(item.creation) }}</span>
          </ListCell>
          <ListCell>
            <StatusBadge :status="statusKey(item.status)" :label="item.status" />
          </ListCell>
        </ListRow>
      </ListRows>
    </List>
  </div>

  <ListPagination v-if="total" v-model:page="page" v-model:page-size="pageSize" :total="total" />

  <EmptyState
    v-if="!ordersRequest.loading && !rows.length"
    icon="lucide-package"
    title="Nothing sent to the provider yet"
    description="Each print job the provider accepts shows up here with the provider's own status."
    :filtered="status !== ALL_ORDERS"
    filtered-title="No provider orders with this status"
    filtered-description="Pick another status, or all orders."
  />
</template>
