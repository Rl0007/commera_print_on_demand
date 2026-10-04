<script>
export const plugin = { label: 'Print jobs', icon: 'printer', requires: 'POD Job', order: 1 }
</script>

<script setup>
import { usePlugin } from '@commera/admin'
import JobDetail from './JobDetail.vue'
import JobList from './JobList.vue'

const { path } = usePlugin()
</script>

<template>
  <JobDetail v-if="path" :key="path" :name="path" />
  <JobList v-else />
</template>
