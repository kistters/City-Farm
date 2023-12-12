import {createApp} from 'vue'
import App from './App.vue'
import axiosPlugin from './plugins/axios';

const app = createApp(App)
app.use(axiosPlugin)
app.mount('#app')