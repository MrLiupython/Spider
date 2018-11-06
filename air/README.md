## 功能说明

核心部分使用pyspider框架

### 爬虫控制面板

http://ip:5000
登陆：在pyspider的webui组件的配置文件中设置，参考pyspider

### 目录说明

- mongo_sync mongodb备份恢复脚本，自动定时运行使用cronjob挂载，实现定期清理过期数据，定期归档数据到目录，一键还原指定日期范围的数据到备份库做分析用（待自动化）
- docker-config pyspider服务,接口服务以及其他必要服务的docker部署文件
- spider_api 封装的从网站获取数据的接口（复杂网站使用pyspidre调用接口的方式抓取）
- requirement 项目依赖以及相关的说明文件
- spider_script  pyspider的爬虫项目的脚本
- squid_proxy_pool 基于squid的代理调度，当前暂时未使用到，可以用分布式部署解决代理问题，也可以使用此脚本创建一个代理服务供pyspider使用

## 部署前

1. 阿里云配置基础的docker节点环境
2. 启动一台机器（manager）安装好docker swarm环境，配置好docker registry（Insecure registries）私库，开启swap(阿里云默认不开启swap，内存不足的时候，ssh会挂掉，导致服务器连不上也无响应，必须去面板重启服务器)
3. 完成基础环境安装后，制作一个docker node使用的镜像，以后新机器都用这个镜像初始化
4. 在manager机器上初始化一个docker swarm 集群，获取manager和workder的token，更新到alicloud_manager_config.sh和alicloud_worker_config.sh
5. 在阿里云设置ecs启动模板，在控制面板添加初始化脚本，使用实例自定义数据功能执行初始化脚本
6. 使用启动模板批量创建节点机器

## 部署

后续可优化方向：直接使用阿里云的集群（参考：https://www.alibabacloud.com/help/zh/doc-detail/25995.htm?spm=a2c63.p38356.a3.2.6b43669alxm4E1）

## 部署方法

直接使用docker swarm构建docker集群，在集群环境内运行pyspider集群（除redis和数据库）、selenium hub和node集群、独立api集群三个独立的集群服务
#### 独立部署的服务，固定服务器，固定ip

1. 数据库
2. mongodb
3. redis

#### 集群部署的服务，动态扩展

```
新部署项目按顺序执行下面的命令
# 初始化swarm集群
docker swarm init
# 创建指定以网卡
docker network create --driver overlay --attachable pyspider_customer_default
# 在node 服务器上运行redis
docker-compose -f service_cn_redis.yml up -d
# 运行独立api项目
docker stack deploy -c service_api.yml api
# 运行selenium项目
docker stack deploy -c selenium-hub-service.yml selenium
# 运行或者更新pyspider项目
docker stack deploy -c service_cn.yml pyspider
```

#### 其他常用docker命令

```
# 列出集群上的所有项目
docker stack ls
# 移除项目
docker stack rm stack_name
(移除独立api项目: docker stack rm api)
# 列出项目详情
docker stack ps stack_name
# 列出集群上的所有节点
docker node ls
# 删除当前节点所有容器：
docker rm -vf $(sudo docker ps -a -q) 
# 删除当前节点所有已经停止的容器: 
docker rm -v $(docker ps -a -q)
# 列出集群manager的toke  
docker swarm join-token -q manager
# 弹性扩容单个服务 把pyspider_webui容器数量改成3个(global模式下强制最多只有一个，replicated模式下可多个)
docker service scale pyspider_webui=3
```

