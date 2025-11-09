# Docker Setup for Frontend

## Prerequisites

1. **Docker Desktop must be running**
   - Open Docker Desktop application
   - Wait until it shows "Docker Desktop is running" in the system tray
   - The Docker whale icon should be steady (not animating)

2. **Port 3000 must be free**
   - Stop any local Vite dev server running on port 3000

## Running the Container

### Option 1: Docker Compose (Recommended)

```powershell
cd frontend
docker-compose up --build
```

### Option 2: Docker directly

```powershell
cd frontend
docker build -t orchestrator-ui .
docker run -p 3000:3000 -v "${PWD}:/app" -v /app/node_modules -e DOCKER=true orchestrator-ui
```

## Troubleshooting

### Docker daemon not responding

If you get: `error during connect: The system cannot find the file specified`

1. **Restart Docker Desktop:**
   - Right-click Docker Desktop icon in system tray
   - Select "Restart"
   - Wait for it to fully start (whale icon stops animating)

2. **Verify Docker is working:**
   ```powershell
   docker ps
   ```
   Should return a list (even if empty), not an error

3. **Check Docker Desktop status:**
   - Open Docker Desktop
   - Check if it shows any errors
   - Make sure WSL 2 backend is enabled (if using WSL)

### Port 3000 already in use

```powershell
# Find process using port 3000
Get-NetTCPConnection -LocalPort 3000 | Select-Object OwningProcess

# Stop the process (replace <PID> with actual process ID)
Stop-Process -Id <PID> -Force
```

### Container builds but doesn't start

Check logs:
```powershell
docker-compose logs frontend
```

### Access the UI

Once running, open: `http://localhost:3000`

## Notes

- The container connects to orchestrator at `host.docker.internal:8000`
- Make sure orchestrator is running on `http://127.0.0.1:8000` on your host
- Code changes will hot-reload automatically (volume mounts)

