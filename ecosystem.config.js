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
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};
