#!/usr/bin/env python3
"""河南师范大学校园网自动认证 by alsjddsg"""

from __future__ import annotations

import argparse
import getpass
import json
import subprocess
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("请先安装依赖：pip install -r requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_PATH = ROOT / "config.example.json"

AUTH_URL = "http://10.101.2.205:8081/aaa-auth/api/v1/auth"
PORTAL = "http://10.101.2.194:6060/"
PROBE_URL = "http://www.msftconnecttest.com/connecttest.txt"
PROBE_OK = "Microsoft Connect Test"
TASK_NAME = "HTUCampusNetLogin"

CAMPUS_CODE = (
    "3def184ad8f4755ff269862ea77393dd,"
    "1afa34a7f984eeabdbb0a7d494132ee5,"
    "65ded5353c5ee48d0b7d48c591b8f430,"
    "fc512637643a493799a7073e4bad6cf8"
)

OPERATORS = {
    "1": ("中国移动", "@yd"),
    "2": ("中国联通", "@lt"),
    "3": ("中国电信", "@dx"),
}

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "http://10.101.2.194:6060",
    "Referer": PORTAL,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"还没有配置文件。先运行：python campus_login.py setup")
        sys.exit(1)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not data.get("username") or not data.get("password"):
        print("username / password 为空，运行 python campus_login.py setup")
        sys.exit(1)
    data.setdefault("operator_suffix", "@yd")
    return data


def save_config(username: str, password: str, operator_suffix: str) -> None:
    payload = {
        "username": username,
        "password": password,
        "operator_suffix": operator_suffix,
    }
    CONFIG_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已写入 {CONFIG_PATH}")


def suffix_label(suffix: str) -> str:
    for name, code in OPERATORS.values():
        if code == suffix:
            return f"{name} ({code})"
    return suffix


def cmd_setup() -> None:
    old = {}
    if CONFIG_PATH.exists():
        try:
            old = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            old = {}
        print("直接回车可保留当前值。\n")

    default_user = old.get("username", "")
    prompt = f"上网账号 [{default_user}]: " if default_user else "上网账号: "
    username = input(prompt).strip() or default_user
    if not username:
        print("账号不能为空")
        sys.exit(1)

    password = getpass.getpass("上网密码（输入时不显示）: ").strip()
    if not password:
        if old.get("password"):
            password = old["password"]
            print("密码未改，沿用原密码。")
        else:
            print("密码不能为空")
            sys.exit(1)

    current_suffix = old.get("operator_suffix", "@yd")
    print("运营商：")
    for key, (name, code) in OPERATORS.items():
        mark = " <- 当前" if code == current_suffix else ""
        print(f"  {key}. {name} ({code}){mark}")
    choice = input("选择 [1/2/3，回车保持当前]: ").strip()
    if choice in OPERATORS:
        suffix = OPERATORS[choice][1]
    elif current_suffix:
        suffix = current_suffix
    else:
        suffix = "@yd"

    save_config(username, password, suffix)
    print(f"账号 {username}，运营商 {suffix_label(suffix)}")


def already_online(session: requests.Session) -> bool:
    try:
        r = session.get(PROBE_URL, timeout=5, allow_redirects=False)
    except requests.RequestException:
        return False
    if r.status_code == 200 and PROBE_OK in r.text:
        return True
    location = r.headers.get("Location", "")
    if "10.101.2.194" in location or "portal.do" in location:
        return False
    try:
        r2 = session.get(PROBE_URL, timeout=5)
        return r2.status_code == 200 and PROBE_OK in r2.text
    except requests.RequestException:
        return False


def login(session: requests.Session, cfg: dict) -> None:
    payload = {
        "campusCode": CAMPUS_CODE,
        "username": cfg["username"],
        "password": cfg["password"],
        "operatorSuffix": cfg["operator_suffix"],
    }
    r = session.post(AUTH_URL, data=payload, headers=HEADERS, timeout=10)
    print(f"auth HTTP {r.status_code}")
    print(r.text[:500])
    r.raise_for_status()
    try:
        data = r.json()
    except ValueError:
        return
    text = json.dumps(data, ensure_ascii=False)
    bad = any(
        k in text.lower()
        for k in ("fail", "error", "invalid", "失败", "错误", "不正确")
    )
    good = any(
        k in text.lower()
        for k in ("success", "ok", "成功", '"code":0', '"code": 0')
    )
    if bad and not good:
        raise SystemExit(f"服务器返回失败: {text[:300]}")


def cmd_login() -> None:
    cfg = load_config()
    session = requests.Session()
    if already_online(session):
        print("已经能上网，不必再登录")
        return
    print(f"未认证，使用 {cfg['username']} / {suffix_label(cfg['operator_suffix'])} 登录…")
    login(session, cfg)
    if already_online(session):
        print("登录成功")
    else:
        print("请求已发出，但探测外网仍失败。")
        sys.exit(2)


def pythonw_path() -> Path:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def cmd_install() -> None:
    if sys.platform != "win32":
        print("开机启动脚本目前只做了 Windows 任务计划。")
        sys.exit(1)
    load_config()
    tr = f'"{pythonw_path()}" "{Path(__file__).resolve()}" login'
    created = subprocess.run(
        [
            "schtasks",
            "/create",
            "/tn",
            TASK_NAME,
            "/tr",
            tr,
            "/sc",
            "ONLOGON",
            "/delay",
            "0000:30",
            "/rl",
            "LIMITED",
            "/f",
        ],
        capture_output=True,
        text=True,
    )
    if created.returncode != 0:
        print(created.stdout)
        print(created.stderr)
        print("创建任务失败。可右键「安装开机启动.bat」选择以管理员身份运行后再试。")
        sys.exit(1)
    print(f"已添加开机任务：{TASK_NAME}")
    print("登录 Windows 约 30 秒后会自动认证。")
    print("删除请运行：python campus_login.py uninstall")


def cmd_uninstall() -> None:
    if sys.platform != "win32":
        print("开机启动脚本目前只做了 Windows。")
        sys.exit(1)
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        print("没找到任务，可能已经删过了。")
        sys.exit(0)
    print(f"已删除开机任务：{TASK_NAME}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="河南师大校园网自动登录")
    parser.add_argument(
        "command",
        nargs="?",
        default="login",
        choices=["login", "setup", "install", "uninstall"],
        help="login 登录 / setup 改账号密码 / install 开机启动 / uninstall 取消开机启动",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "setup":
        cmd_setup()
    elif args.command == "install":
        cmd_install()
    elif args.command == "uninstall":
        cmd_uninstall()
    else:
        cmd_login()


if __name__ == "__main__":
    main()
