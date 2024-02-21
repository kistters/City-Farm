<template>
  <div id="secret-page">
    <div class="centered-content">
      <FarmDashboard />
      <CityDashboard />

    </div>
    <router-view></router-view>
  </div>
</template>
<script>

import FarmDashboard from "@/components/FarmDashboard";
import CityDashboard from "@/components/CityDashboard";

export default {
  name: 'SecretPage',
  components: {FarmDashboard, CityDashboard}
}
</script>

<style scoped>
#secret-page {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 325px;
}

.centered-content {
  margin-bottom: 20px;
  display: flex;
  gap: 50px;
}
</style>