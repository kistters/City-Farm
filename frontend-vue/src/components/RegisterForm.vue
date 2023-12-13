<template>
  <div>
    <form @submit.prevent="submitForm">
      <input type="text" v-model="username" placeholder="Username"/>
      <input type="password" v-model="password" placeholder="Password"/>
      <input type="password" v-model="password2" placeholder="Confirm Password"/>
      <button type="submit">Register</button>
    </form>
  </div>
</template>

<style scoped>
input {
  margin-bottom: 5px;
  display: block;
}
</style>

<script>
export default {
  name: 'RegisterForm',
  data() {
    return {
      username: '',
      password: '',
      password2: '',
    }
  },
  computed: {
    isAuthenticated() {
      return !!this.authToken;
    }
  },
  methods: {
    async submitForm() {
      this.$axios.post('/v1/register/', {
        username: this.username,
        password: this.password,
        password2: this.password2
      }, {})
          .then(function (response) {
            console.log(response);
          })
          .catch(function (error) {
            if (error.response) {
              // The request was made and the server responded with a status code
              console.log(error.response.data);    // Here is where the error message will be in
              console.log(error.response.status);  // 400
              console.log(error.response.headers);
            } else if (error.request) {
              // The request was made but no response was received
              console.log(error.request);
            } else {
              // Something happened in setting up the request that triggered an Error
              console.log('Error', error.message);
            }
            console.log('Error config', error.config);
          });

    }
  }
}
</script>