import { createSSRApp } from "vue"
import App from "./App.vue"
import { memberPageGuard } from "./utils/session.js"

export function createApp() {
  const app = createSSRApp(App)
  // uni-app page lifecycle mixins also cover shared/deep-linked pages.
  app.mixin({ onShow: memberPageGuard })
  return { app }
}
