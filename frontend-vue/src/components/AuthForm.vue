<template>
  <div>
    <div class="tab-options" v-if="!isAuthenticated">
      <div class="tab-option" :class="formChoice === 'login' ? 'active' : ''" @click="formChoice = 'login'">Login</div>
      <div class="tab-option" :class="formChoice === 'register' ? 'active' : ''" @click="formChoice = 'register'">
        Register
      </div>
      <div class="tab-option" :class="formChoice === 'forgot' ? 'active' : ''" @click="formChoice = 'forgot'">Forgot</div>
    </div>

    <div class="form-box" v-if="!isAuthenticated && formChoice === 'login'">
      <form @submit.prevent="loginForm">
        <input type="text" v-model="username" placeholder="Username"/>
        <input type="password" v-model="password" placeholder="Password"/>
        <button type="submit">Login</button>
      </form>

    </div>

    <div class="form-box" v-if="!isAuthenticated && formChoice === 'register'">
      <form @submit.prevent="registerForm">
        <input type="text" v-model="username" placeholder="Username"/>
        <input type="password" v-model="password" placeholder="Password"/>
        <input type="password" v-model="password2" placeholder="Confirm Password"/>
        <button type="submit">Register</button>
      </form>
    </div>

    <div class="form-box" v-if="!isAuthenticated && formChoice === 'forgot'">
      <form @submit.prevent="forgotForm">
        <input type="text" v-model="email" placeholder="Email"/>
        <button type="submit">Forgot</button>
      </form>
    </div>

    <button v-if="isAuthenticated" @click="logout">Log out</button>
  </div>
</template>

<style scoped>
.tab-options {
  display: flex;
}

.tab-option {
  padding: 5px;
  border: 1px solid #dae1e7;
  cursor: pointer;
}

.tab-option.active {
  background-color: #dae1e7;
}

.form-box {
  border: 1px solid #dae1e7;
  padding: 15px;
  height: 100px;
  position: relative;
}

.form-content {
  overflow: auto;
}

.form-box input, .form-box button {
  display: block;
  text-align: left;
  margin-bottom: 5px;
}

</style>

<script>
export default {
  name: 'AuthForm',
  data() {
    return {
      username: '',
      email: '',
      password: '',
      password2: '',
      authToken: localStorage.getItem('authToken') || '',
      formChoice: 'login'
    }
  },
  computed: {
    isAuthenticated() {
      return !!this.authToken;
    }
  },
  methods: {
    async registerForm() {
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

    },
    async loginForm() {
      try {
        const response = await this.$axios.post('/v1/login/', {
          username: this.username,
          password: this.password
        });
        this.authToken = response.data.token;
        localStorage.setItem('authToken', this.authToken);
      } catch (error) {
        console.log('Login failed: ', error);
      }
    },
    async logout() {
      this.$axios.post('/v1/logout/',).then(() => {
        this.authToken = '';
        this.username = '';
        this.password = '';
        this.password2 = '';
        localStorage.removeItem('authToken');
      });
    },
    async forgotForm() {
      alert('not implemented yet')
    },
  }
}
</script>