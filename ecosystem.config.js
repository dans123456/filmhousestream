const path = require("path");

module.exports = {
  apps: [
    {
      name: "filmhouse-stream-bot",
      script: "venv/bin/python3",
      args: "main.py",
      cwd: __dirname,
      interpreter: "none",
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true,
      watch: false,
    },
    {
      name: "filmhouse-tunnel",
      script: "/usr/local/bin/cloudflared",
      args: `tunnel --url http://127.0.0.1:8080 --logfile ${path.join(__dirname, "tunnel.log")}`,
      cwd: __dirname,
      interpreter: "none",
      restart_delay: 5000,
      autorestart: true,
    },
  ],
};
