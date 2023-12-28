<template>
  <div id="broadcast-dashboard">

    <div class="dashboard-boxes">
      <div class="dashboard-box top-farmer">
        <h2>Top Farmer</h2>
        <div v-for="(entry, index) in insightFarmer" :key="index">
          <b>{{ entry.username }} : </b>
          <span>{{ entry.score }}</span>
        </div>
      </div>

      <div class="dashboard-box missing-ingredients">
        <h2>Missing Ingredients</h2>
        <div v-for="(message, index) in missingIngredients" :key="index">
          <span>{{ message }}</span>
        </div>
      </div>

      <div class="dashboard-box top-citizen">
        <h2>Top Citizen</h2>
        <div v-for="(entry, index) in insightCitizen" :key="index">
          <b>{{ entry.username }}:</b> <!-- Name -->
          <span>{{ entry.score }}</span> <!-- Score -->
        </div>
      </div>

    </div>

    <!--    <ul>-->
    <!--      <li v-for="(message, index) in messages" :key="index">{{ message }}</li>-->
    <!--    </ul>-->
    <router-view></router-view>
  </div>
</template>

<style scoped>
.dashboard-boxes {
  display: flex;
  gap: 10px;
}

.dashboard-box {
  flex: 0 0 25%;
  border: 1px solid #ccc;
  padding: 10px;
  box-shadow: 2px 2px 10px #eee;
  border-radius: 5px;
}

.missing-ingredients {
  height: 200px;
  overflow-y: auto;
}
</style>

<script>
export default {
  name: 'BroadcastDashboard',
  data() {
    return {
      connection_ready: null,
      connection_error: null,
      socket: null,
      messages: [],
      retryIn: 3000, // Retry connection every 3 seconds

      insightFarmer: [],
      insightCitizen: [],
      missingIngredients: [],
    };
  },
  methods: {
    init_chat() {
      this.socket = new WebSocket("ws://api.cityfarm.com/ws/status/");
      this.socket.onopen = this.onSocketOpen;
      this.socket.onmessage = this.onSocketMessage;
      this.socket.onerror = this.onSockerError;
      this.socket.onclose = this.onSocketClose;
    },
    onSocketOpen(event) {
      console.log(event);
      this.socket.send(JSON.stringify({message: {'dashboard': 'start'}}));
      this.connection_ready = true;
    },
    onSocketMessage(event) {
      var insights = JSON.parse(event.data)
      this.insightFarmer = insights.top_farmer ?? this.insightFarmer
      this.insightCitizen = insights.top_citizen ?? this.insightCitizen

      this.missingIngredients.unshift(insights.missing_ingredient)

      console.log(JSON.parse(event.data));
    },
    onSockerError(event) {
      console.log(event);
      setTimeout(() => this.init_chat(), this.retryIn); // Retry connection after 2 seconds
    },
    onSocketClose() {
      console.log('Socket closed, retrying...');
      setTimeout(() => this.init_chat(), this.retryIn); // Retry connection after 2 seconds
    }
  },
  mounted() {
    this.init_chat();
  },
}
;
</script>