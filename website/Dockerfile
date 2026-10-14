# NEXT_PUBLIC_API_URL is inlined at build time, so it is a build arg.
FROM node:22-alpine AS build
WORKDIR /app
COPY website/package*.json ./
RUN npm ci
COPY website .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "run", "start"]
