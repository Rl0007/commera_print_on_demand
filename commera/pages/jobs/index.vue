<script>
export const extension = { label: 'Print jobs', icon: 'printer', requires: 'POD Job', order: 1 }
</script>

<script setup>
import { useExtension } from '@commera/admin'
import JobDetail from './JobDetail.vue'
import JobList from './JobList.vue'

const { path } = useExtension()
</script>

<template>
  <JobDetail v-if="path" :key="path" :name="path" />
  <JobList v-else />
</template>
