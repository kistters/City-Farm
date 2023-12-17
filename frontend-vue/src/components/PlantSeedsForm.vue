<template>
  <div>
    <form @submit.prevent="submitForm">
      <input type="text" v-model="ingredientName" placeholder="Ingredient Seed"/>
      <button type="submit">Plant Seeds</button>
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
  name: 'PlantSeedsForm',
  data() {
    return {
      ingredientName: '',
    }
  },
  methods: {
    async submitForm() {
      this.$axios.post('/v1/produce-ingredient/', {
        name: this.ingredientName,
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