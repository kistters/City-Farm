<template>
  <div id="home-page">
    <div class="centered-content">
      <PlantSeedsForm/>
    </div>
    <div class="centered-content">
      <BroadcastDashboard/>
    </div>
    <router-view></router-view>
  </div>
</template>
<script>

import PlantSeedsForm from "@/components/PlantSeedsForm.vue";
import BroadcastDashboard from "@/components/BroadcastDashboard.vue";

export default {
  name: 'HomePage',
  components: {BroadcastDashboard, PlantSeedsForm}
}
</script>

<style scoped>
#home-page {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
      height: 325px;
}

.centered-content {
  margin-bottom: 20px;
}
</style>