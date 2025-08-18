# Face Detection Server - Docker Setup

This guide explains how to run the Face Detection Server using Docker.

## 📋 Prerequisites

- Docker installed on your system
- Docker Compose (usually included with Docker Desktop)
- A webcam connected to your system
- For Linux users: proper video device permissions

## 🚀 Quick Start

### 1. Build and Run with Docker Compose

```bash
# Clone/navigate to your project directory
cd face-detection-project

# Build and start the server
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 2. Access the Application

- **Web Interface**: http://localhost:8080
- **API Endpoints**: Available at http://localhost:8080/
- **WebSocket**: ws://localhost:8080

### 3. Stop the Application

```bash
# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## 🔧 Manual Docker Commands

### Build the Image

```bash
docker build -t face-detection-server .
```

### Run the Container

```bash
# Basic run
docker run -p 8080:8080 face-detection-server

# With camera access (Linux/macOS)
docker run --privileged \
  --device=/dev/video0:/dev/video0 \
  -p 8080:8080 \
  -v $(pwd)/logs:/app/logs \
  face-detection-server

# Windows (with USB camera)
docker run --privileged \
  -p 8080:8080 \
  -v ${PWD}/logs:/app/logs \
  face-detection-server
```

## 🎛️ Configuration Options

### Environment Variables

You can customize the behavior using environment variables:

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - FLASK_ENV=production
  - CAMERA_INDEX=0
  - SERVER_PORT=8080
  - DEBUG=false
```

### Volume Mounts

- `./logs:/app/logs` - Persist log files
- `./config:/app/config` - Custom configuration files
- `/dev:/dev` - Camera device access (Linux/macOS)

### Port Mapping

Change the port mapping if 8080 is already in use:

```yaml
ports:
  - "9090:8080"  # Access via http://localhost:9090
```

## 🐳 Docker Compose Profiles

### Run with Client Container

```bash
# Start server and client
docker-compose --profile with-client up --build

# The client will automatically connect to the server
```

### Production Mode

```bash
# Run optimized for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🔍 Troubleshooting

### Camera Access Issues

**Linux:**
```bash
# Check camera permissions
ls -l /dev/video*

# Add user to video group
sudo usermod -a -G video $USER

# Run with proper permissions
docker run --privileged --device=/dev/video0 ...
```

**macOS:**
```bash
# Grant Docker access to camera in System Preferences
# Security & Privacy > Camera > Docker

# Use host networking if needed
docker run --network host ...
```

**Windows:**
```bash
# Use Docker Desktop with proper USB settings
# Enable "Use Windows containers" if needed
```

### Port Already in Use

```bash
# Find what's using port 8080
netstat -tulpn | grep :8080

# Use different port
docker run -p 8081:8080 face-detection-server
```

### Container Logs

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs face-detection-server

# Container logs directly
docker logs face-detection-server
```

## 🧪 Development Setup

### Development with Hot Reload

```yaml
# Add to docker-compose.override.yml
services:
  face-detection-server:
    volumes:
      - .:/app
    environment:
      - FLASK_ENV=development
    command: ["python", "-u", "face_detection_server.py"]
```

### Debugging

```yaml
# Add debugging ports
ports:
  - "8080:8080"
  - "5678:5678"  # For debugger
environment:
  - PYTHONPATH=/app
  - DEBUG=true
```

## 🏗️ Multi-Stage Build (Advanced)

For production optimization, you can use a multi-stage build:

```dockerfile
# Build stage
FROM python:3.9 as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
# ... rest of production setup
```

## 📊 Monitoring

### Health Checks

```bash
# Check container health
docker ps
# Look for "healthy" status

# Manual health check
curl http://localhost:8080/status
```

### Resource Monitoring

```bash
# Monitor resource usage
docker stats face-detection-server

# View running processes
docker exec -it face-detection-server ps aux
```

## 🔐 Security Considerations

1. **Non-root User**: The container runs as a non-root user for security
2. **Privileged Mode**: Only use `--privileged` when necessary for camera access
3. **Network Isolation**: Use custom networks to isolate containers
4. **Secrets Management**: Use Docker secrets for sensitive data

## 🚀 Production Deployment

### With Docker Swarm

```bash
# Deploy to swarm
docker stack deploy -c docker-compose.yml face-detection

# Scale the service
docker service scale face-detection_face-detection-server=3
```

### With Kubernetes

```bash
# Generate Kubernetes manifests
docker-compose config > k8s-manifests.yml

# Apply to cluster
kubectl apply -f k8s-manifests.yml
```

## 📁 Project Structure

```
face-detection-project/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── face_detection_server.py
├── client.py
├── logs/                    # Persisted logs
└── config/                  # Configuration files
    └── app.conf
```

## 🤝 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs`
3. Verify camera permissions and device access
4. Ensure Docker has sufficient resources allocated
5. Check firewall/antivirus settings

---

**Happy Dockerizing! 🐳**