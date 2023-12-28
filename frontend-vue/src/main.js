import {createApp} from 'vue'
import App from './App.vue'
import axiosPlugin from './plugins/axios';
import router from "@/routes";

createApp(App)
    .use(axiosPlugin)
    .use(router)
    .mount('#app')