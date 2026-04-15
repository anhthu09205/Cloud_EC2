
#!/bin/bash
echo "Dừng toàn bộ container đang chạy..."
docker ps -q | grep -q . && docker stop $(docker ps -q)
echo "Xóa sạch container cũ để chạy project mới..."
docker ps -aq | grep -q . && docker rm -f $(docker ps -aq)
echo "Kiểm tra lại Docker còn container không..."
docker ps 
echo "Chạy tất cả container (web, app, proxy, db, keycloak,...) "
docker compose build --no-cache 
docker compose up -d 
docker compose ps