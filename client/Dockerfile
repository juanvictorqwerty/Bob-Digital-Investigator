# syntax=docker/dockerfile:1

# Use Bun image for base image for all stages.
ARG BUN_VERSION=1.2.6
FROM oven/bun:${BUN_VERSION} as base

# Set working directory for all build stages.
WORKDIR /usr/src/app

################################################################################
# Create a stage for installing production dependencies.
FROM base as deps

# Download dependencies as a separate step to take advantage of Docker's caching.
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=bun.lock,target=bun.lock \
    --mount=type=cache,target=/root/.bun \
    bun install --frozen-lockfile --production

################################################################################
# Create a stage for building the application.
FROM deps as build

# Download additional development dependencies before building.
RUN --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=bun.lock,target=bun.lock \
    --mount=type=cache,target=/root/.bun \
    bun install --frozen-lockfile

# Copy the rest of the source files into the image.
COPY . .

# Add environment variables
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}

# Run the build script.
RUN bun run build

################################################################################
# Create a new stage to run the application with minimal runtime dependencies
FROM base as final

# Use production environment by default.
ENV NODE_ENV production

# Run the application as a non-root user.
USER bun

# Copy package.json so that package manager commands can be used.
COPY package.json .

# Copy the production dependencies from the deps stage and also
# the built application from the build stage into the image.
COPY --from=deps /usr/src/app/node_modules ./node_modules
COPY --from=build /usr/src/app/.next ./.next
COPY --from=build /usr/src/app/public ./public
COPY --from=build /usr/src/app/next.config.ts ./next.config.ts

# Expose the port that the application listens on.
EXPOSE 3000

# Run the application.
CMD bun run start --host 0.0.0.0