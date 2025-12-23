#!/bin/bash
#
# Run Django management commands in production containerized environment
#
# This script runs initialization and maintenance commands for ColdFront.
# It should be run after the first deployment and can be run again safely
# (most commands are idempotent).
#
# Usage:
#   ./bootstrap/production/docker/scripts/run_django_commands.sh
#

set -e  # Exit on error

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-bootstrap/production/docker/docker-compose.yml}"
WEB_CONTAINER="${WEB_CONTAINER:-coldfront-web}"

echo "=================================================="
echo "Running Django Management Commands"
echo "=================================================="
echo "Compose file: $COMPOSE_FILE"
echo "Web container: $WEB_CONTAINER"
echo ""

# Function to run a Django management command
run_command() {
    local cmd="$1"
    local description="$2"

    echo "---------------------------------------------------"
    echo "Running: $description"
    echo "Command: python manage.py $cmd"
    echo "---------------------------------------------------"

    docker compose -f "$COMPOSE_FILE" exec "$WEB_CONTAINER" python manage.py $cmd

    if [ $? -eq 0 ]; then
        echo "✓ Success: $description"
    else
        echo "✗ Failed: $description"
        return 1
    fi
    echo ""
}

# Check if web container is running
echo "Checking if web container is running..."
if ! docker ps | grep -q "$WEB_CONTAINER"; then
    echo "Error: Web container '$WEB_CONTAINER' is not running."
    echo "Start it with: docker compose -f $COMPOSE_FILE up -d"
    exit 1
fi
echo "✓ Web container is running"
echo ""

# Run migrations first (always)
run_command "migrate" "Database migrations"

# Run initialization commands
run_command "initial_setup" "Initial setup (creates default data)"
run_command "add_accounting_defaults" "Add accounting defaults"
run_command "create_allocation_periods" "Create allocation periods"
run_command "add_allowance_defaults" "Add allowance defaults"
run_command "add_directory_defaults" "Add directory defaults"
run_command "create_staff_group" "Create staff group"

# Collect static files
run_command "collectstatic --noinput" "Collect static files"

# Optional: Schedule periodic tasks (uncomment if needed)
# run_command "schedule_allocation_period_audits" "Schedule allocation period audits"

echo "=================================================="
echo "All Django management commands completed!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Verify application is accessible: http://localhost:8000"
echo "  2. Check health endpoint: http://localhost:8000/health/"
echo "  3. Create a superuser (if needed):"
echo "     docker compose -f $COMPOSE_FILE exec $WEB_CONTAINER python manage.py createsuperuser"
echo ""
