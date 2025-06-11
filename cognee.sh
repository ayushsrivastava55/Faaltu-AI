version: '3.8'

services:
  neo4j:
    image: neo4j:2025.05.0  # Match your APOC version
    container_name: neo4j-apoc-extended
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - ./neo4j/data:/data
      - ./neo4j/logs:/logs
      - ./neo4j/plugins:/plugins  # Contains apoc-*-extended.jar
      - ./neo4j/conf:/conf
    environment:
      # Authentication
      - NEO4J_AUTH=neo4j/cognee123
      
      # Security configuration for APOC (REQUIRED!)
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      
      # APOC configuration
      - NEO4J_apoc_export_file_enabled=true
      - NEO4J_apoc_import_file_enabled=true
      - NEO4J_apoc_import_file_use__neo4j__config=true
      
      # Memory settings
      - NEO4J_server_memory_pagecache_size=2G
      - NEO4J_server_memory_heap_max__size=2G
    restart: unless-stopped