#!/bin/bash
set -e

# change work directory to env or prod
cd ~/backend

# Convert multiple arguments for docker compose to short function
run_compose() {
    # merge yaml files for production
    local compose_files="-f docker-compose.yml -f docker/docker-compose.server.yml"
    local project_name="dev"
    # run command
    docker compose \
        -p "${project_name}" \
        ${compose_files} \
        "$@"
}


echo "Build new web image"
run_compose build web -q

echo "Start all production containers with new web container"
run_compose up -d

# if some container addresses changed, caddy restart is necessary
run_compose restart caddy

#wait for health checking
sleep 5

#show final result
run_compose ps

echo "Remove dangling images"
docker image prune -f

