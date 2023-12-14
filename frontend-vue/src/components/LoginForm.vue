<template>
  <div>
    <form @submit.prevent="submitForm" v-if="!isAuthenticated">
      <input type="text" v-model="username" placeholder="Username"/>
      <input type="password" v-model="password" placeholder="Password"/>
      <button type="submit">Login</button>
      <p v-if="loginError">Login Failed</p>
    </form>
    <button v-else @click="logout">Log out</button>
  </div>
</template>

<style scoped>
  input {
    margin-right: 5px;
  }
</style>

<script>
export default {
  name: 'LoginForm',
  data() {
    return {
      username: '',
      password: '',
      loginError: false,
      authToken: localStorage.getItem('authToken') || '',
    }
  },
  computed: {
    isAuthenticated() {
      return !!this.authToken;
    }
  },
  methods: {
    async submitForm() {
      try {
        const response = await this.$axios.post('/v1/login/', {
          username: this.username,
          password: this.password
        });
        this.authToken = response.data.token;
        this.loginError = false;
        localStorage.setItem('authToken', this.authToken);
      } catch (error) {
        console.log('Login failed: ', error);
        this.loginError = true;
      }
    },
    async logout() {
      this.$axios.post('/v1/logout/',).then(() => {
        this.authToken = '';
        localStorage.removeItem('authToken');
      });
    }
  }
}
</script>