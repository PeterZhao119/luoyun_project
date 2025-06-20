## 启动实例
### 前置步骤
```
# python虚拟环境
source myenv/bin/activate

# docker
sudo systemctl start docker
sudo systemctl enable docker

# 数据库
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v /home/ecs-user/luoyun/mongodb/data:/data/db \
  mongo:5.0.5
```
## 启动服务
### mongo
```
docker start mongodb
```
### ecloud
```
bash 
```