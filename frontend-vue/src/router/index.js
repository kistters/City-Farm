import {createWebHistory, createRouter} from "vue-router";
import SecretPage from "@/views/SecretPage";
import HomePage from "@/views/HomePage";

const routes = [{
    path: "/", name: "HomePage", component: HomePage,
}, {
    path: "/secret-page", name: "SecretPage", component: SecretPage,
}];

const router = createRouter({
    history: createWebHistory(), routes,
});

export default router;