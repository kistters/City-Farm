const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    allowedHosts: [
      'cityfarm.com',  // Allow subdomains of example.com
      '0.0.0.0' // Allow local IP
    ]
  }
})
