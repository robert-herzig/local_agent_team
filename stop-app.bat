@echo off
echo Stopping AI Chat Application...
echo.

docker-compose -f docker-compose.dev.yml down

echo.
echo Application stopped successfully.
echo.
echo To remove all containers and images, run:
echo   docker-compose -f docker-compose.dev.yml down --rmi all --volumes
echo.
pause
