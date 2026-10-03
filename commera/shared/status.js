// StatusBadge colours by the dashboard's own status keys, so each job status borrows the closest one.
const STATUS_KEYS = {
  Queued: 'draft',
  Submitted: 'pending',
  'In Production': 'packed',
  Received: 'pending',
  Shipped: 'shipped',
  Delivered: 'delivered',
  Cancelled: 'cancelled',
}

export const statusKey = (status) => STATUS_KEYS[status] ?? 'draft'
