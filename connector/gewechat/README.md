服务器:
14.103.202.202
root/Chitic@2899
说明：
1.第一次登录时需要清空gewechat_app_id和gewechat_token，登录后会自动填充，后续重启程序可复用，无需再次登录；
2.暂时单独运行gewechat_connector模块的方式进行登录测试
3.gewechat已docker运行，不用管
运行：
目录：/luoyun
环境：conda activate luoyun
命令：python -m connector.gewechat.gewechat_connector
后台运行：nohup python -m connector.gewechat.gewechat_connector.py & tail -f wechat.out