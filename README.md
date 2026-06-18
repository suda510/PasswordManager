# PasswordManager

本地优先、离线可用的桌面密码管理器。

## 功能

- 主密码加密保护
- 添加 / 编辑 / 删除密码条目
- 按网站/软件名快速搜索
- 一键复制用户名和密码
- 恢复密钥找回主密码
- AES-GCM 加密存储

## 技术栈

- Python 3.12+
- PyQt5 + PyQt-Fluent-Widgets（Fluent Design 风格）
- SQLite + AES-GCM 加密
- PyInstaller 打包为单个 exe

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python -m app.main
```

## 打包

```bash
# 生成图标（首次）
python scripts/generate_icon.py

# 打包为 exe
pyinstaller build.spec
```

生成的 `dist/PasswordManager.exe` 即为独立可执行文件。

## 项目结构

```
PasswordManager/
├── app/
│   ├── main.py              # 入口
│   ├── core/
│   │   ├── crypto.py        # 加密/解密
│   │   ├── db.py            # 数据库操作
│   │   ├── models.py        # 数据模型
│   │   └── config_manager.py# 配置管理
│   ├── ui/
│   │   ├── login_window.py  # 登录窗口
│   │   ├── main_window.py   # 主窗口
│   │   ├── dialogs.py       # 对话框
│   │   ├── styles.py        # 样式定义
│   │   └── icon_gen.py      # 图标生成
│   └── utils/
│       ├── clipboard.py     # 剪贴板操作
│       └── paths.py         # 路径管理
├── assets/                  # 图标资源
├── scripts/
│   └── generate_icon.py     # 图标生成脚本
├── requirements.txt
└── build.spec               # PyInstaller 配置
```

## 安全设计

- 主密码通过 PBKDF2 派生加密密钥
- 敏感字段使用 AES-GCM 加密存储
- 主密码仅存储不可逆哈希
- 支持恢复密钥找回
