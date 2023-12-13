<template>
  <div id="user-register">
    <h1>This is the User Register page</h1>
    <RegisterForm></RegisterForm>
    <router-view></router-view>
  </div>
</template>
<script>
import RegisterForm from "@/components/RegisterForm";
export default {
  name: "UserRegister",
  components: { RegisterForm },
};
</script>
<style scoped>
</style>