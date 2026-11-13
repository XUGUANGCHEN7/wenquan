const labels = { OPEN: "今日营业中", NOT_OPEN: "今日未营业", CLOSED: "今日已打烊", REST: "今日休息" }

export function businessPresentation(data) {
  return {
    label: labels[data?.status] || "营业状态待确认",
    isOpen: data?.status === "OPEN",
    hours: data?.opens_at && data?.closes_at
      ? `营业时间 ${data.opens_at}—${data.closes_at}` : "营业时间待确认",
  }
}
