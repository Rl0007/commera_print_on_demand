<script setup>
import { computed } from 'vue'
import { Skeleton } from 'frappe-ui'
import { EmptyState, StatusBadge, shortDate, useExtension, useMethodRead, usePage } from '@commera/admin'
import { statusKey } from '../../shared/status'

const props = defineProps({
  name: { type: String, required: true },
})

const { navigate } = useExtension()

const jobRequest = useMethodRead('commera_print_on_demand.api.get_job', {
  params: { name: props.name },
})

const job = computed(() => jobRequest.data)

const pageHeader = usePage()
pageHeader.setTitle(props.name)
pageHeader.setBreadcrumbs([{ label: 'Print jobs', to: 'jobs' }, { label: props.name }])
pageHeader.setActions(() =>
  job.value
    ? [{ label: 'Open order', icon: 'receipt', onClick: () => navigate(`/orders/${job.value.sales_order}`) }]
    : [],
)

const jobFacts = computed(() => [
  { label: 'Order', value: job.value.sales_order },
  { label: 'Item', value: job.value.item_code },
  { label: 'Product', value: job.value.product_id || '—' },
  { label: 'Quantity', value: job.value.qty },
  { label: 'Created', value: shortDate(job.value.creation) },
])

const providerFacts = computed(() => {
  const order = job.value.provider_order
  return [
    { label: 'External ID', value: order.external_id || '—' },
    { label: 'Product', value: order.product_id || '—' },
    { label: 'Quantity', value: order.qty },
    { label: 'Received', value: shortDate(order.creation) },
  ]
})
</script>

<template>
  <div class="mx-auto max-w-4xl">
    <Skeleton v-if="jobRequest.loading && !job" class="h-40 w-full rounded-5" />

    <EmptyState
      v-else-if="!job"
      icon="lucide-printer"
      title="This print job couldn't be found"
      description="It may have been deleted, or you may not have access to it."
    />

    <div v-else class="space-y-6">
      <section class="rounded-5 border border-outline-gray-1">
        <div class="flex items-center justify-between px-4 py-3">
          <h2 class="text-lg-semibold text-ink-gray-8">Job</h2>
          <StatusBadge :status="statusKey(job.status)" :label="job.status" />
        </div>
        <div class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
          <div v-for="fact in jobFacts" :key="fact.label" class="flex justify-between gap-3 px-4 py-3">
            <span class="text-base text-ink-gray-5">{{ fact.label }}</span>
            <span class="truncate text-base text-ink-gray-8 tabular-nums">{{ fact.value }}</span>
          </div>
        </div>
      </section>

      <section class="rounded-5 border border-outline-gray-1">
        <div class="flex items-center justify-between px-4 py-3">
          <h2 class="text-lg-semibold text-ink-gray-8">Provider order</h2>
          <StatusBadge
            v-if="job.provider_order"
            :status="statusKey(job.provider_order.status)"
            :label="job.provider_order.status"
          />
        </div>
        <div v-if="job.provider_order" class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
          <div v-for="fact in providerFacts" :key="fact.label" class="flex justify-between gap-3 px-4 py-3">
            <span class="text-base text-ink-gray-5">{{ fact.label }}</span>
            <span class="truncate text-base text-ink-gray-8 tabular-nums">{{ fact.value }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          compact
          icon="lucide-package"
          title="Not sent to the provider yet"
          description="The job is queued until the provider accepts it."
        />
      </section>
    </div>
  </div>
</template>
