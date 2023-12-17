<template>
  <div id="broadcast-dashboard">
    <ul>
      <li v-for="(message, index) in messages" :key="index">{{ message }}</li>
    </ul>
    <router-view></router-view>
  </div>
</template>
<script>
export default {
  name: 'BroadcastDashboard',
  data() {
    return {
      connection_ready: null,
      connection_error: null,
      socket: null,
      messages: [],
      retryIn: 2000 // Retry connection every 2 seconds
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
      this.connection_ready = true;
    },
    onSocketMessage(event) {
      console.log(event.data);
      this.messages.unshift(event.data);
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