# syntax=docker/dockerfile:1
FROM eclipse-temurin:17-jdk

WORKDIR /app

# Copy the Spring Boot app source
COPY csp/ /app/csp/

# ENV JAVA_TOOL_OPTIONS="-Xmx8g"

# Build the Spring Boot app
WORKDIR /app/csp
RUN ./mvnw clean package -DskipTests

# Expose port
EXPOSE 8000

# Run the Spring Boot app with custom properties
CMD ["./mvnw", "spring-boot:run", "-Dspring-boot.run.arguments=--server.port=8000", "-Dspring.security.user.password="] 