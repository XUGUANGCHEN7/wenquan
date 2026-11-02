export type Role = "frontdesk" | "merchant" | "finance" | "admin"

export function canAccess(allowed: Role[] | undefined, role: Role | null): boolean {
  if (!role) return false
  return allowed === undefined || allowed.includes(role)
}
