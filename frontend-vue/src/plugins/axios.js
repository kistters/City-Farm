import axios from "axios";

const instance = axios.create({
    baseURL: 'http://api.cityfarm.com',
});

instance.interceptors.request.use(async (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
        config.headers['Authorization'] = `Token ${token}`
    }
    return config;
}, (error) => {
    return Promise.reject(error)
});


export default {
    install: (app, options) => {
        app.config.globalProperties.$axios = instance;
        console.log(options)
    }
};