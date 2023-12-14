import {createWebHistory, createRouter} from "vue-router";
import UserRegister from "@/views/UserRegister.vue";
import Home from "@/views/Home.vue";

const routes = [{
    path: "/", name: "Home", component: Home,
}, {
    path: "/user-register", name: "UserRegister", component: UserRegister,
}];

const router = createRouter({
    history: createWebHistory(), routes,
});

export default router;