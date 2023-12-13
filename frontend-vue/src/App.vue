<template>
  <div id="app">
    <div id="nav">
      <div id="links">
        <router-link to="/">Home</router-link>
        <router-link to="/secret-page">Secret Page</router-link>
      </div>
      <AuthForm></AuthForm>
    </div>
    <router-view/>
  </div>
</template>

<script>

import AuthForm from "@/components/AuthForm";

export default {
  name: 'App',
  components: {AuthForm}
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