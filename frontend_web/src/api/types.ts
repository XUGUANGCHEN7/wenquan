export interface Order {
  order_no: string
  order_type: string
  business_id: string | null
  status: string
  amount_cents: number
  payment_method: string | null
  created_at: string
  paid_at: string | null
}

export interface RoomBoardItem {
  id: string
  number: string
  status: string
  room_use_id: string | null
  booking_id: string | null
  actual_end_at: string | null
  cleaning_end_at: string | null
}

export interface FoodOrder extends Order {
  id: string
  food_order_id: string
  fulfillment_status: string
  exception_reason: string | null
  room_number: string
  delivered_at: string | null
  items: Array<{ name_snapshot: string; quantity: number; unit_price_cents: number }>
}

export interface AccessOverview {
  cards: Array<{ id: string; physical_uid: string; status: string }>
  lockers: Array<{ id: string; number: string; status: string }>
  deposits: Array<{ id: string; ticket_id: string; amount_cents: number; status: string; refund_id: string | null }>
  bindings: Array<{ id: string; card_id: string; locker_id: string; deposit_id: string; room_use_id: string | null; status: string }>
  device_tasks: Array<{ id: string; task_no: string; task_type: string; status: string; raw_error: string }>
}

export interface Exceptions {
  refunds: Array<{ refund_no: string; status: string; amount_cents: number }>
  paid_exceptions: Array<{ order_no: string; order_type: string; amount_cents: number; status: string }>
  device_unknown: Array<{ id: string; task_no: string; raw_error: string }>
  room_conflicts: Array<{ id: string; order_id: string; status: string }>
  food_delivery: Array<{ id: string; reason: string }>
}
