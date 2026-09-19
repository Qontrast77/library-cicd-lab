@echo off
"%DOCKER%" compose build
"%DOCKER%" login -u %DOCKERHUB_USER% -p %DOCKERHUB_PASS%
"%DOCKER%" push %IMAGE_NAME%:%IMAGE_TAG%
"%DOCKER%" tag %IMAGE_NAME%:%IMAGE_TAG% %IMAGE_NAME%:latest
"%DOCKER%" push %IMAGE_NAME%:latest
"%DOCKER%" logout
