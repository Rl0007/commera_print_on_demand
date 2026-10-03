<script>
export const extension = {
  label: 'Resend to printer',
  icon: 'printer',
  requires: 'POD Job',
  condition: 'commera_print_on_demand.conditions.has_resendable_jobs',
  method: 'commera_print_on_demand.api.resend_order',
  confirm: "Send this order's print jobs to the printer again? Jobs already in production are left alone.",
}
</script>
