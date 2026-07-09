FROM node:18-alpine

# Create app directory and set ownership
WORKDIR /app

COPY package.json .
RUN npm install --include=optional
# Change ownership to node user
RUN chown -R node:node /app
USER node

COPY . .

EXPOSE 5173

CMD ["npm","run","dev","--","--host","0.0.0.0"]