module.exports = {
  apps: [
    {
      name: "filmhouse-stream-bot",
      script: "venv/bin/python3",
      args: "main.py",
      cwd: "/home/ubuntu/filmhouse-stream-bot",
      interpreter: "none",
      restart_delay: 5000,
      max_restarts: 10,
      autorestart: true,
      watch: false,
    },
    {
      name: "filmhouse-tunnel",
      script: "/usr/local/bin/cloudflared",
      args: "tunnel --url http://127.0.0.1:8088 --logfile /home/ubuntu/filmhouse-stream-bot/tunnel.log",
      cwd: "/home/ubuntu/filmhouse-stream-bot",
      interpreter: "none",
      restart_delay: 5000,
      autorestart: true,
    },
  ],
};
