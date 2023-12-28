<template>
  <div>
    <div class="toggle">
      <input type="radio" id="produce" value="produce" v-model="action">
      <label for="produce">Produce</label>
      <input type="radio" id="buy" value="buy" v-model="action">
      <label for="buy">Buy</label>
    </div>
    <div class="grid">
      <button
          v-for="ingredient in ingredients"
          :key="ingredient"
          @click="submitForm(ingredient)"
          class="button-ingredient"
      >
        {{ ingredient }}
      </button>
    </div>
  </div>

</template>

<style scoped>
.grid {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 3px;
  max-width: 250px;
}

.button-ingredient {
  margin-bottom: 5px;
  display: block;
  width: 70px; /* Define the width according to your requirement */
  height: 25px; /* Define the height according to your requirement */
  text-align: center;
}

.toggle {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 10px;
}

.toggle input[type="radio"] {
  display: none;
}

.toggle label {
  padding: 10px 20px;
  margin: 0;
  cursor: pointer;
  color: #666;
  transition: background 0.3s;
}

.toggle input[type="radio"]:checked + label {
  background: #2196F3;
  color: #fff;
}
</style>

<script>
export default {
  name: 'PlantSeedsForm',
  data() {
    return {
      action: 'buy',
      ingredients: [
        'tomato', 'carrot', 'corn', 'potato', 'broccoli',
        'banana', 'apple', 'grape', 'orange'
      ],
    }
  },

  methods: {
    async submitForm(ingredient) {
      this.$axios.post(`/v1/${this.action.toLowerCase()}-ingredient/`, {
        name: ingredient,
      }, {})
          .then(function (response) {
            console.log(response);
          })
          .catch(function (error) {
            if (error.response) {
              console.log(error.response.data);
              console.log(error.response.status);
              console.log(error.response.headers);
            } else if (error.request) {
              console.log(error.request);
            } else {
              console.log('Error', error.message);
            }
            console.log('Error config', error.config);
          });
    }
  }
}
</script>