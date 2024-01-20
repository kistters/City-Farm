<template>
  <div>
    <div class="grid">
      <button
          v-for="{id, name} in commodities"
          :key="id"
          @click="produceFood(id)"
          class="button-produce"
      >
        {{ name }}
      </button>
    </div>
    <div class="grid">
      <la>
        <li :key="id" v-for="{id, name, summary} in commoditySummary">
          {{ summary }} - ({{ name }})
        </li>
      </la>
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
  border: 1px solid #ccc;
}

.button-produce {
  margin: 5px;
  display: block;
  width: 70px; /* Define the width according to your requirement */
  height: 25px; /* Define the height according to your requirement */
  text-align: center;
}
</style>

<script>
export default {
  name: 'CommoditiesForm',
  data() {
    return {
      commodities: [],
      commoditySummary: [],
    }
  },

  created() {
    this.$axios.get('/v1/farm/commodities/')
        .then((response) => {
          this.commodities = response.data
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

    this.$axios.get('/v1/farm/summary/')
        .then((response) => {
          this.commoditySummary = response.data
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
  },

  methods: {
    async produceFood(commodityId) {

      this.$axios.post(`/v1/farm/food/`, {
        commodity: commodityId,
      }, {})
          .then((response) => {
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