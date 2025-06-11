# Voice-to-Text AI Assistant Deployment Guide

This guide provides instructions for deploying the Voice-to-Text AI Assistant in various environments.

## Prerequisites

- Python 3.8+
- Neo4j database (4.4+)
- OpenAI API key
- Docker (optional, for containerized deployment)

## Environment Setup

1. Clone the repository or copy the application files to your deployment environment.

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure environment variables by creating a `.env` file in the backend directory:
   ```
   # API Keys
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Neo4j Connection
   NEO4J_URI=bolt://your_neo4j_host:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   
   # Server Settings
   HOST=0.0.0.0
   PORT=8000
   DEBUG=False
   
   # LLM Settings
   LLM_MODEL=gpt-4o
   LLM_TEMPERATURE=0.2
   
   # Logging Settings
   LOG_LEVEL=INFO
   ```

## Deployment Options

### Option 1: Direct Deployment with Uvicorn

For simple deployments or development environments:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option 2: Deployment with Gunicorn and Uvicorn Workers

For production environments:

1. Install Gunicorn:
   ```bash
   pip install gunicorn
   ```

2. Create a `gunicorn_config.py` file:
   ```python
   workers = 4
   worker_class = "uvicorn.workers.UvicornWorker"
   bind = "0.0.0.0:8000"
   timeout = 120
   ```

3. Start the server:
   ```bash
   gunicorn -c gunicorn_config.py main:app
   ```

### Option 3: Docker Deployment

1. Create a `Dockerfile` in the project root:
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY backend/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY backend/ .
   
   EXPOSE 8000
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. Build and run the Docker container:
   ```bash
   docker build -t voice-to-text-assistant .
   docker run -p 8000:8000 --env-file backend/.env voice-to-text-assistant
   ```

### Option 4: Kubernetes Deployment

1. Create a Kubernetes deployment YAML file:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: voice-to-text-assistant
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: voice-to-text-assistant
     template:
       metadata:
         labels:
           app: voice-to-text-assistant
       spec:
         containers:
         - name: voice-to-text-assistant
           image: voice-to-text-assistant:latest
           ports:
           - containerPort: 8000
           envFrom:
           - secretRef:
               name: voice-to-text-assistant-secrets
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: voice-to-text-assistant-service
   spec:
     selector:
       app: voice-to-text-assistant
     ports:
     - port: 80
       targetPort: 8000
     type: LoadBalancer
   ```

2. Create a Kubernetes secret for environment variables:
   ```bash
   kubectl create secret generic voice-to-text-assistant-secrets \
     --from-literal=OPENAI_API_KEY=your_openai_api_key \
     --from-literal=NEO4J_URI=bolt://your_neo4j_host:7687 \
     --from-literal=NEO4J_USER=neo4j \
     --from-literal=NEO4J_PASSWORD=your_neo4j_password
   ```

3. Apply the deployment:
   ```bash
   kubectl apply -f deployment.yaml
   ```

## Monitoring and Scaling

### Health Checks

The application provides a `/health` endpoint that can be used to monitor the health of the service. This endpoint checks the connection to Neo4j and returns the status of the application.

### Scaling Considerations

1. **Database Scaling**: Consider using Neo4j Causal Cluster for high availability and scalability of the knowledge graph.

2. **Application Scaling**: The application can be horizontally scaled by deploying multiple instances behind a load balancer.

3. **Caching**: For high-traffic deployments, consider implementing a caching layer (e.g., Redis) to cache frequent queries and responses.

## Security Considerations

1. **API Keys**: Ensure that API keys and sensitive credentials are stored securely and not exposed in code or logs.

2. **CORS Configuration**: Update the CORS settings in `config.py` to restrict access to trusted origins only.

3. **Rate Limiting**: Consider implementing rate limiting to prevent abuse of the API.

4. **Input Validation**: Ensure that all user inputs are properly validated and sanitized.

## Troubleshooting

1. **Database Connection Issues**: Verify that Neo4j is running and accessible from the application server. Check the connection string and credentials.

2. **OpenAI API Issues**: Ensure that the OpenAI API key is valid and has sufficient quota.

3. **Memory Usage**: If the application is using too much memory, consider adjusting the number of workers or implementing memory optimization strategies.

4. **Logging**: Check the application logs for errors and warnings. The log level can be adjusted in the `.env` file.

## Conclusion

This deployment guide provides a starting point for deploying the Voice-to-Text AI Assistant in various environments. Depending on your specific requirements, you may need to adapt these instructions to fit your infrastructure and deployment practices.
