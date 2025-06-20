## 部署 - 新建实例

### Ssh
在服务器上生成sshkey，并且回填到github代码仓库的deploy token

### Git
```
sudo apt update
sudo apt install -y git
git clone git@github.com:PeterZhao119/luoyun.git
```

### docker
```
sudo apt-get update
sudo apt install -y docker.io

sudo systemctl start docker
sudo systemctl enable docker

sudo usermod -aG docker $USER
newgrp docker
```
在这里复制加速器地址
https://cr.console.aliyun.com/cn-shanghai/instances/mirrors


```
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://9saya7mb.mirror.aliyuncs.com"
  ]
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
docker info | grep -A 2 "Registry Mirrors"
```

### mongo
启动
```
docker pull mongo:5.0.5
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v /home/ecs-user/luoyun/mongodb/data:/data/db \
  mongo:5.0.5
```

进入数据库
```
docker exec -it mongodb mongosh
use mymongo
```

重启数据库
```
docker restart mongodb
```

### python安装和依赖
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11

sudo apt update
sudo apt install -y python3.11-venv

python3 -m venv myenv
source myenv/bin/activate

pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip3 config set global.trusted-host mirrors.aliyun.com

pip3 install -r luoyun/requirements.txt