import {createWebHistory, createRouter} from "vue-router";
import HomePage from "@/views/HomePage.vue";
import SecretPage from "@/views/SecretPage";

const ifAuthenticated = (to, from, next) => {
    if (sessionStorage.getItem('authToken')) {
        next();
        return;
    }
    next('/');
};


const routes = [
    {path: "/", name: "HomePage", component: HomePage,},
    {path: "/secret", name: "SecretPage", component: SecretPage, beforeEnter: ifAuthenticated}
];

const router = createRouter({
    history: createWebHistory(), routes,
});

export default router;