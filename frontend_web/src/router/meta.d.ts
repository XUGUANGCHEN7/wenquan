import "vue-router"
import type { Role } from "./access"

declare module "vue-router" {
  interface RouteMeta {
    roles?: Role[]
    public?: boolean
  }
}
