# 河南师范大学校园网自动登录 by alsjddsg

开机或手动运行后，向学校认证接口提交账号，省去每次打开 Portal 页面点登录。

> 个人自用脚本。账号仅存本机

## 环境

- Windows 10 / 11
- Python 3.8+
- 已连接到河南师大校园网（会弹出 `10.101.2.194:6060` 登录页的那种）

```bat
pip install -r requirements.txt
```

## 第一次使用

1. 双击 `修改账号密码.bat`（或 `python campus_login.py setup`）
2. 输入上网账号、密码，选择运营商
   - 移动 `@yd`
   - 联通 `@lt`
   - 电信 `@dx`
3. 双击 `立即登录.bat` 试一次

也可以直接复制 `config.example.json` 为 `config.json` 再手工改。

## 开机自启

| 操作 | 方式 |
| --- | --- |
| 添加 | 双击 `安装开机启动.bat` |
| 删除 | 双击 `卸载开机启动.bat` |

安装后会在「任务计划程序」里生成任务 `HTUCampusNetLogin`：每次登录 Windows 约 30 秒后静默认证。已经能上网则脚本直接退出。

命令行等价：

```bat
python campus_login.py install
python campus_login.py uninstall
```

## 命令

```bat
python campus_login.py          登录（默认）
python campus_login.py login    同上
python campus_login.py setup    修改账号 / 密码 / 运营商
python campus_login.py install  添加开机启动
python campus_login.py uninstall 删除开机启动
```

## 原理

登录页在 `http://10.101.2.194:6060/`，实际认证接口：

```
POST http://10.101.2.205:8081/aaa-auth/api/v1/auth
Content-Type: application/x-www-form-urlencoded
```

字段：`campusCode`、`username`、`password`、`operatorSuffix`。

先访问 `http://www.msftconnecttest.com/connecttest.txt` 判断是否已放行，避免重复登录。

`campusCode` 来自一次真实登录抓包，一般是学校固定值。若学校改认证系统，需要重新抓 `auth` 请求。

## 注意

- 校园网通常限制同时在线设备数，电脑登录可能把手机踢下线
- 不要把含密码的 `config.json` 发到群里或公开仓库
- 接口变更后本脚本会失效，以浏览器里实际请求为准
