<template>
  <div id="secret-page">
    <div class="centered-content">
      <FarmDashboard/>

    </div>
    <router-view></router-view>
  </div>
</template>
<script>

import FarmDashboard from "@/components/FarmDashboard";

export default {
  name: 'SecretPage',
  components: {FarmDashboard}
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
}
</style>