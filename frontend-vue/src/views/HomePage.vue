<template>
  <div id="home-page">
    <div id="feed-container">
      <BroadcastDashboard/>

    </div>
    <router-view></router-view>
  </div>
</template>
<script>

import BroadcastDashboard from "@/components/BroadcastDashboard.vue";

export default {
  name: 'HomePage',
  components: {BroadcastDashboard}
}
</script>

<style scoped>
#feed-container {
  width: 50%; /* Use full width */
  height: 70vh; /* Use full viewport height */
  overflow-y: auto; /* Enable vertical scrollbar if content overflows */
  scrollbar-width: thin; /* Optional: make the scrollbar thin */
  scrollbar-color: lightgray; /* Optional: change scrollbar color */
  border: 2px solid black; /* Change 'black' to desired border color */

}
</style>