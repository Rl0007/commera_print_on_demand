<script>
export const plugin = {
  label: 'Print status',
  requires: 'POD Job',
  condition: 'commera_print_on_demand.conditions.has_print_jobs',
}
</script>

<script setup>
import { computed, watch } from 'vue'
import { Skeleton } from 'frappe-ui'
import { StatusBadge, useCard, usePlugin, useMethodRead } from '@commera/admin'
import { statusKey } from '../../../shared/status'

const { record } = usePlugin()
const card = useCard()

const jobsRequest = useMethodRead('commera_print_on_demand.api.get_order_print_jobs', {
  params: () => ({ sales_order: record.value.name }),
})

const jobs = computed(() => jobsRequest.data ?? [])

watch(
  () => jobsRequest.data,
  (rows) => card.setHidden(rows && !rows.length),
)
</script>

<template>
  <Skeleton v-if="jobsRequest.loading && !jobsRequest.data" class="h-16 w-full rounded-4" />
  <div v-else class="divide-y divide-outline-gray-1">
    <div v-for="job in jobs" :key="job.name" class="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0">
      <div class="min-w-0">
        <p class="truncate text-base text-ink-gray-8">{{ job.item_code }} × {{ job.qty }}</p>
        <p class="truncate text-sm text-ink-gray-5 tabular-nums">{{ job.name }}</p>
      </div>
      <StatusBadge :status="statusKey(job.status)" :label="job.status" />
    </div>
  </div>
</template>
