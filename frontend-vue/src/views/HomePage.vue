<template>
  <div id="home-page">
    <form @submit.prevent="sendMessageForm">
      <input type="text" v-model="message" placeholder="message"/>
      <button type="submit">send</button>
    </form>
    <ul>
      <li v-for="(message, index) in messages" :key="index">{{ message }}</li>
    </ul>
    <router-view></router-view>
  </div>
</template>
<script>
export default {
  data() {
    return {
      socket: null,
      message: null,
      messages: [],
    };
  },
  created() {
    const self = this; // preserve the context

    this.socket = new WebSocket("ws://api.cityfarm.com/ws/status/");

    this.socket.onmessage = function (event) {
      self.messages.push(event.data);
    };

    this.socket.onerror = function (error) {
      console.log(`WebSocket error: ${error}`);
    };

    this.socket.onclose = function (event) {
      if (event.wasClean) {
        console.log(`Connection closed cleanly, code=${event.code}, reason=${event.reason}`);
      } else {
        // e.g. server process killed or network down, event.code is usually 1006 in this case
        console.log('Connection closed abnormally');
      }
    };
  },
  beforeUnmount() {
    // Close the WebSocket connection when the Vue instance is unmounted
    if (this.socket !== null && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
      console.log("close websocket")
    }
  },
  methods: {
    sendMessageForm() {
      this.socket.send(this.message);
    }
  }
};
</script>