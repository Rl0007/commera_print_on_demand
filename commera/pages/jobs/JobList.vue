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
  useExtension,
  useMethodRead,
  usePage,
} from '@commera/admin'
import { statusKey } from '../../shared/status'

const ALL_JOBS = 'all'
const ROW_HEIGHT = 60

const { navigate } = useExtension()
const pageHeader = usePage()
pageHeader.setTitle('Print jobs')
pageHeader.setBreadcrumbs([])
pageHeader.setActions([{ label: 'Provider orders', icon: 'package', onClick: () => navigate('provider-orders') }])

const status = ref(ALL_JOBS)
const page = ref(1)
const pageSize = ref(20)

const jobsRequest = useMethodRead('commera_print_on_demand.api.get_jobs', {
  params: () => ({
    status: status.value === ALL_JOBS ? undefined : status.value,
    start: (page.value - 1) * pageSize.value,
    page_length: pageSize.value,
  }),
  refetch: true,
})

watch(status, () => (page.value = 1))

const rows = computed(() => jobsRequest.data?.rows ?? [])
const total = computed(() => jobsRequest.data?.total ?? 0)

const statusOptions = computed(() => {
  const counts = jobsRequest.data?.counts ?? {}
  const allCount = Object.values(counts).reduce((sum, count) => sum + count, 0)
  return [
    { label: `All jobs (${allCount})`, value: ALL_JOBS },
    ...Object.entries(counts).map(([name, count]) => ({ label: `${name} (${count})`, value: name })),
  ]
})

const skeletonColumns = window.matchMedia('(max-width: 639.98px)').matches ? 2 : 6
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <Select v-model="status" :options="statusOptions" />
  </div>

  <div class="mt-3 overflow-x-auto">
    <List
      class="max-sm:[--list-columns:minmax(0,1fr)_auto] sm:min-w-[54rem]"
      :row-height="ROW_HEIGHT"
      :columns="['1fr', '11rem', '9rem', '5rem', '7rem', '8rem']"
    >
      <ListHeader>
        <ListHeaderCell>Job</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Order</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Product</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Qty</ListHeaderCell>
        <ListHeaderCell class="max-sm:hidden">Created</ListHeaderCell>
        <ListHeaderCell>Status</ListHeaderCell>
      </ListHeader>

      <ListSkeleton v-if="jobsRequest.loading && !rows.length" :columns="skeletonColumns" />

      <ListRows v-else :items="rows" row-key="name" v-slot="{ item }">
        <ListRow :value="item.name" @click="navigate(`jobs/${item.name}`)">
          <ListCell>
            <div class="min-w-0">
              <p class="truncate text-base text-ink-gray-8">{{ item.item_code }}</p>
              <p class="truncate text-sm text-ink-gray-4 tabular-nums">{{ item.name }}</p>
            </div>
          </ListCell>
          <ListCell class="max-sm:hidden">
            <span class="truncate text-base text-ink-gray-7 tabular-nums">{{ item.sales_order }}</span>
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
    v-if="!jobsRequest.loading && !rows.length"
    icon="lucide-printer"
    title="No print jobs yet"
    description="An order with a print-on-demand product creates a job here and sends it to the provider."
    :filtered="status !== ALL_JOBS"
    filtered-title="No jobs with this status"
    filtered-description="Pick another status, or all jobs."
  />
</template>
