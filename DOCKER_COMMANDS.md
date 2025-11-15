# Docker Commands Cheat Sheet

Quick reference for managing your CodeGraph Docker containers.

## Starting & Stopping

### Start Everything
```bash
docker-compose up -d
```
- Starts Neo4j + Backend
- `-d` runs in background (detached)

### Stop Everything
```bash
docker-compose down
```
- Stops all containers
- Keeps data (volumes persist)

### Stop and Remove All Data
```bash
docker-compose down -v
```
- ⚠️ **WARNING:** Deletes all graph data!
- Use when you want to start fresh

### Restart Everything
```bash
docker-compose restart
```

### Restart Specific Service
```bash
docker-compose restart neo4j
docker-compose restart backend
```

## Viewing Status & Logs

### Check Status
```bash
docker-compose ps
```
Shows running containers and their status

### View All Logs
```bash
docker-compose logs -f
```
- `-f` follows logs in real-time
- Press `Ctrl+C` to exit

### View Specific Service Logs
```bash
docker-compose logs -f neo4j
docker-compose logs -f backend
```

### View Last 50 Lines
```bash
docker-compose logs --tail=50 neo4j
```

## Building & Updating

### Rebuild Containers
```bash
docker-compose up -d --build
```
Use when you change code or Dockerfile

### Pull Latest Images
```bash
docker-compose pull
```
Updates to latest Neo4j version

### Force Recreate Containers
```bash
docker-compose up -d --force-recreate
```

## Container Management

### List All Containers
```bash
docker ps
docker ps -a  # Include stopped containers
```

### Stop Individual Container
```bash
docker stop codegraph-neo4j
docker stop codegraph-backend
```

### Start Individual Container
```bash
docker start codegraph-neo4j
docker start codegraph-backend
```

### Remove Individual Container
```bash
docker rm codegraph-neo4j
docker rm codegraph-backend
```

### Execute Command in Container
```bash
docker exec -it codegraph-neo4j bash
docker exec -it codegraph-backend bash
```

## Volume Management

### List Volumes
```bash
docker volume ls
```

### Inspect Volume
```bash
docker volume inspect graph-db-for-codebase_neo4j_data
```

### Remove Unused Volumes
```bash
docker volume prune
```
⚠️ Careful! This removes all unused volumes

### Backup Neo4j Data
```bash
docker run --rm \
  -v graph-db-for-codebase_neo4j_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/neo4j-backup.tar.gz /data
```

### Restore Neo4j Data
```bash
docker run --rm \
  -v graph-db-for-codebase_neo4j_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/neo4j-backup.tar.gz -C /
```

## Troubleshooting

### Check Container Health
```bash
docker inspect codegraph-neo4j | grep -A 10 Health
```

### View Container Resource Usage
```bash
docker stats
```

### Remove All Stopped Containers
```bash
docker container prune
```

### Remove All Unused Images
```bash
docker image prune -a
```

### Full Cleanup (Everything!)
```bash
docker system prune -a --volumes
```
⚠️ **WARNING:** Removes everything Docker-related!

### Check Port Usage
```bash
# Windows
netstat -ano | findstr :7474
netstat -ano | findstr :7687
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :7474
lsof -i :7687
lsof -i :8000
```

## Common Workflows

### Fresh Start
```bash
# Stop and remove everything
docker-compose down -v

# Start fresh
docker-compose up -d

# Wait for startup
docker-compose logs -f neo4j
# Look for: "Remote interface available at http://localhost:7474/"
```

### Update Code and Restart
```bash
# After changing code in backend/
docker-compose restart backend
```

### Check if Everything is Running
```bash
# 1. Check containers
docker-compose ps

# 2. Check Neo4j
curl http://localhost:7474

# 3. Check backend
curl http://localhost:8000/health
```

### Development Workflow
```bash
# Start
docker-compose up -d

# Work on code...

# View logs while developing
docker-compose logs -f backend

# Restart after changes
docker-compose restart backend

# Stop when done
docker-compose down
```

## Quick Reference

| Task | Command |
|------|---------|
| Start | `docker-compose up -d` |
| Stop | `docker-compose down` |
| Restart | `docker-compose restart` |
| Logs | `docker-compose logs -f` |
| Status | `docker-compose ps` |
| Rebuild | `docker-compose up -d --build` |
| Fresh start | `docker-compose down -v && docker-compose up -d` |

## Accessing Services

| Service | URL | Login |
|---------|-----|-------|
| Neo4j Browser | http://localhost:7474 | neo4j / password |
| Backend API | http://localhost:8000 | N/A |
| API Docs | http://localhost:8000/docs | N/A |
| ReDoc | http://localhost:8000/redoc | N/A |

## Environment Variables

Edit in `.env` or `docker-compose.yml`:

```env
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

After changing, restart:
```bash
docker-compose down
docker-compose up -d
```

## Tips

1. **Always use `-d`** to run in background
2. **Check logs** if something doesn't work: `docker-compose logs -f`
3. **Wait 30 seconds** for Neo4j to fully start
4. **Use `down -v`** only when you want to delete all data
5. **Keep Docker Desktop running** in the background

## Emergency Commands

### Nothing works - start over:
```bash
docker-compose down -v
docker system prune -a
docker-compose up -d
```

### Port conflict:
```bash
# Edit docker-compose.yml and change ports:
ports:
  - "7475:7474"  # Change 7474 to 7475
  - "7688:7687"  # Change 7687 to 7688
```

### Container won't start:
```bash
# Remove and recreate
docker-compose down
docker rm -f codegraph-neo4j codegraph-backend
docker-compose up -d
```

---

**Most used command:**
```bash
docker-compose up -d && docker-compose logs -f
```

This starts everything and shows logs so you can see when it's ready! 🚀
