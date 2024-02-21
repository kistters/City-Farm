<template>
  <div>
    <div class="grid">
      <button
          v-for="{id, name} in jobs"
          :key="id"
          @click="doTheWork(id)"
          class="button-do-the-work"
      >
        {{ name }}
      </button>
    </div>
    <div class="grid">
      <la>
        <li :key="id" v-for="{id, name, summary} in jobsSummary">
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

.button-do-the-work {
  margin: 5px;
  display: block;
  text-align: center;
}
</style>

<script>
export default {
  name: 'CityDashboard',
  data() {
    return {
      jobs: [],
      jobsSummary: [],
    }
  },

  created() {
    this.$axios.get('/v1/jobs/')
        .then((response) => {
          this.jobs = response.data
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

    this.$axios.get('/v1/job-summary/')
        .then((response) => {
          this.jobsSummary = response.data
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
    async doTheWork(jobId) {

      this.$axios.post(`/v1/do-the-work/`, {
        job: jobId,
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