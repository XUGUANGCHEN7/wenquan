export function orderDetailUrl(order, example = false) {
  const id = order.id || order.order_no
  if (!id) throw new Error("缺少订单标识")
  return `/pages/orders/detail?id=${encodeURIComponent(id)}${example ? "&example=1" : ""}`
}
