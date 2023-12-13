<template>
  <div id="app">
    <div id="nav">
      <div id="links">
        <router-link to="/">Home</router-link> |
        <router-link to="/user-register">User Register</router-link>
      </div>
      <LoginForm />
    </div>
    <router-view />
  </div>
</template>

<script>
import LoginForm from "@/components/LoginForm";

export default {
  name: 'App',
  components: { LoginForm }
}
</script>

<style>
#app {
  display: flex;
  flex-direction: column;
  align-items: stretch; /* if you want your content to stretch to the edge of their container, otherwise omit */
}

#nav {
  display: flex;
  justify-content: space-between;
}

#links {
  display: flex;
  gap: 10px; /* distace between links */
}
</style>