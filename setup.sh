#!/bin/bash

# Neo4j APOC Extended Docker Setup Script
# This script automates the setup of Neo4j with APOC Extended plugin

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate version format
validate_version() {
    if [[ $1 =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]+$ ]] || [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to get APOC version from Neo4j version
get_apoc_version() {
    local neo4j_version=$1
    # For 2025.x versions, use exact match
    if [[ $neo4j_version =~ ^2025\. ]]; then
        echo "${neo4j_version%.*}.0"
    else
        # For 5.x versions, use exact match
        echo "$neo4j_version"
    fi
}

echo "=========================================="
echo "  Neo4j APOC Extended Setup Script"
echo "=========================================="
echo

# Check prerequisites
print_info "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_warning "docker-compose not found. Checking for 'docker compose'..."
    if ! docker compose version >/dev/null 2>&1; then
        print_error "Neither docker-compose nor 'docker compose' is available."
        exit 1
    else
        DOCKER_COMPOSE_CMD="docker compose"
        print_info "Using 'docker compose' command."
    fi
else
    DOCKER_COMPOSE_CMD="docker-compose"
    print_info "Using 'docker-compose' command."
fi

if ! command_exists wget && ! command_exists curl; then
    print_error "Neither wget nor curl is available. Please install one of them."
    exit 1
fi

print_success "Prerequisites check passed!"
echo

# Get Neo4j version from user
while true; do
    read -p "Enter Neo4j version (e.g., 2025.05.0, 5.13.0): " NEO4J_VERSION
    if validate_version "$NEO4J_VERSION"; then
        break
    else
        print_error "Invalid version format. Please use format like '2025.05.0' or '5.13.0'"
    fi
done

# Calculate APOC version
APOC_VERSION=$(get_apoc_version "$NEO4J_VERSION")
print_info "Neo4j version: $NEO4J_VERSION"
print_info "APOC Extended version: $APOC_VERSION"

# Get password
read -s -p "Enter Neo4j password: " NEO4J_PASSWORD
echo
if [ -z "$NEO4J_PASSWORD" ]; then
    print_error "Password cannot be empty."
    exit 1
fi

# Choose installation method
echo
print_info "Choose installation method:"
echo "1. Manual JAR download (Recommended for production)"
echo "2. Automatic download (Development only)"
read -p "Enter choice (1 or 2): " INSTALL_METHOD

case $INSTALL_METHOD in
    1)
        INSTALL_TYPE="manual"
        print_info "Selected: Manual JAR download"
        ;;
    2)
        INSTALL_TYPE="automatic"
        print_info "Selected: Automatic download"
        print_warning "This method is only recommended for development environments."
        ;;
    *)
        print_error "Invalid choice. Please enter 1 or 2."
        exit 1
        ;;
esac

echo

# Create directory structure
print_info "Creating directory structure..."
mkdir -p ./neo4j/{data,logs,plugins,conf}
chmod 755 ./neo4j/plugins

if [ "$INSTALL_TYPE" = "manual" ]; then
    # Download APOC Extended JAR
    print_info "Downloading APOC Extended JAR..."
    
    APOC_JAR="apoc-${APOC_VERSION}-extended.jar"
    DOWNLOAD_URL="https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/${APOC_VERSION}/${APOC_JAR}"
    
    print_info "Download URL: $DOWNLOAD_URL"
    
    cd ./neo4j/plugins
    
    if command_exists wget; then
        if wget -O "$APOC_JAR" "$DOWNLOAD_URL"; then
            print_success "Downloaded $APOC_JAR"
        else
            print_error "Failed to download APOC Extended JAR. Please check:"
            print_error "1. Internet connectivity"
            print_error "2. Version compatibility"
            print_error "3. URL: $DOWNLOAD_URL"
            exit 1
        fi
    else
        if curl -L -o "$APOC_JAR" "$DOWNLOAD_URL"; then
            print_success "Downloaded $APOC_JAR"
        else
            print_error "Failed to download APOC Extended JAR. Please check:"
            print_error "1. Internet connectivity"
            print_error "2. Version compatibility"
            print_error "3. URL: $DOWNLOAD_URL"
            exit 1
        fi
    fi
    
    # Set JAR permissions
    chmod 644 "$APOC_JAR"
    print_success "Set permissions for $APOC_JAR"
    
    cd ../..
fi

# Create docker-compose.yml
print_info "Creating docker-compose.yml..."

cat > docker-compose.yml << EOF
version: '3.8'

services:
  neo4j:
    image: neo4j:${NEO4J_VERSION}
    container_name: neo4j-apoc-extended
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - ./neo4j/data:/data
      - ./neo4j/logs:/logs
      - ./neo4j/plugins:/plugins
      - ./neo4j/conf:/conf
    environment:
      # Authentication
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      
EOF

if [ "$INSTALL_TYPE" = "automatic" ]; then
    cat >> docker-compose.yml << EOF
      # APOC Extended auto-download (development only)
      - NEO4JLABS_PLUGINS=["apoc-extended"]
      
EOF
fi

cat >> docker-compose.yml << EOF
      # Security configuration for APOC (REQUIRED!)
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      
      # APOC configuration
      - NEO4J_apoc_export_file_enabled=true
      - NEO4J_apoc_import_file_enabled=true
      - NEO4J_apoc_import_file_use__neo4j__config=true
      
      # Memory settings (adjust as needed)
      - NEO4J_server_memory_pagecache_size=1G
      - NEO4J_server_memory_heap_max__size=1G
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ${NEO4J_PASSWORD} 'RETURN 1'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
EOF

print_success "Created docker-compose.yml"

# Start the container
print_info "Starting Neo4j container..."
if $DOCKER_COMPOSE_CMD up -d; then
    print_success "Container started successfully!"
else
    print_error "Failed to start container. Check the logs with: $DOCKER_COMPOSE_CMD logs"
    exit 1
fi

# Wait for Neo4j to be ready
print_info "Waiting for Neo4j to be ready..."
sleep 10

# Check if container is running
if [ "$($DOCKER_COMPOSE_CMD ps -q neo4j)" ]; then
    print_success "Neo4j container is running"
else
    print_error "Neo4j container is not running. Check logs with: $DOCKER_COMPOSE_CMD logs neo4j"
    exit 1
fi

# Verify APOC installation
print_info "Verifying APOC Extended installation..."
sleep 20  # Give more time for Neo4j to fully start

# Test APOC procedures
if docker exec neo4j-apoc-extended cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "CALL apoc.help('help') YIELD name RETURN count(name) as procedure_count" > /dev/null 2>&1; then
    print_success "APOC Extended is working correctly!"
else
    print_warning "APOC verification failed. This might be normal if Neo4j is still starting up."
    print_info "You can manually verify later with:"
    print_info "docker exec -it neo4j-apoc-extended cypher-shell -u neo4j -p [password]"
    print_info "Then run: CALL apoc.help('help') YIELD name RETURN name LIMIT 10;"
fi

echo
print_success "Setup completed!"
echo
print_info "Access Neo4j Browser at: http://localhost:7474"
print_info "Username: neo4j"
print_info "Password: [the password you entered]"
echo
print_info "Useful commands:"
print_info "- View logs: $DOCKER_COMPOSE_CMD logs neo4j"
print_info "- Stop container: $DOCKER_COMPOSE_CMD down"
print_info "- Restart container: $DOCKER_COMPOSE_CMD restart neo4j"
print_info "- Enter container: docker exec -it neo4j-apoc-extended bash"
echo
print_info "Test APOC Extended with these Cypher queries:"
print_info "CALL apoc.help('help') YIELD name RETURN name LIMIT 10;"
print_info "CALL apoc.config.list() YIELD name, value WHERE name STARTS WITH 'apoc' RETURN name, value;"

echo
print_success "Neo4j with APOC Extended is ready to use!"