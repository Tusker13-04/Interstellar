# Start from Ubuntu:22.04 as the base image
FROM ubuntu:22.04

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install common dependencies
RUN apt-get update && \
    apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Setup Node.js repository and install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get update && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package.json and requirements.txt first
COPY package*.json ./
COPY requirements.txt ./

# Install dependencies
RUN npm install --legacy-peer-deps && \
    npm install cors --legacy-peer-deps && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Node.js application in the background\n\
npm start &\n\
NODE_PID=$!\n\
\n\
# Start Python application in the foreground\n\
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
PYTHON_PID=$!\n\
\n\
# Handle termination signals\n\
trap "kill $NODE_PID $PYTHON_PID; exit" SIGINT SIGTERM\n\
\n\
# Wait for any process to exit\n\
wait -n\n\
\n\
# Exit with status of process that exited first\n\
exit $?' > /app/start.sh && \
    chmod +x /app/start.sh

# Expose ports for both applications
EXPOSE 8000 3000

# Run the startup script
CMD ["/app/start.sh"]
