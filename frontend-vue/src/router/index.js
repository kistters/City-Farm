import {createWebHistory, createRouter} from "vue-router";
import UserRegister from "@/views/UserRegister";
import HomePage from "@/views/HomePage";

const routes = [{
    path: "/", name: "HomePage", component: HomePage,
}, {
    path: "/user-register", name: "UserRegister", component: UserRegister,
}];

const router = createRouter({
    history: createWebHistory(), routes,
});

export default router;