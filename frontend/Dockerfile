FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json .
RUN npm install

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Install serve globally
RUN npm install -g serve

# Expose port
EXPOSE 3000

# Serve the production build
CMD serve -s dist -l ${PORT:-3000}
