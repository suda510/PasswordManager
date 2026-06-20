# PasswordManager

[English](#english) | [中文](#中文)

---

## 中文

本地优先、离线可用的桌面密码管理器。

### 功能

- 🔐 主密码加密保护（PBKDF2 + AES-256-GCM）
- 📝 密码条目增删改查
- 📁 分组管理（创建、重命名、删除）
- 🔍 快速搜索（关键词高亮）
- 📋 一键复制用户名/密码/网址（30秒自动清除剪贴板）
- 👁 密码显隐切换
- 📤 CSV 明文导出
- 🔑 恢复密钥找回主密码
- 🔒 锁定功能
- 🎨 Fluent Design 风格 UI

### 技术栈

- Python 3.12+
- PyQt5（原生，无额外 UI 框架依赖）
- SQLite + AES-256-GCM 加密
- PyInstaller 打包为单个 exe（约 40MB）

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python -m app.main
```

### 打包

```bash
# 生成图标（首次）
python scripts/generate_icon.py

# 打包为 exe
pyinstaller build.spec
```

### 项目结构

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
│   │   ├── notification.py  # 通知组件
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

### 安全设计

- 主密码通过 PBKDF2（600,000 次迭代）派生加密密钥
- 敏感字段使用 AES-256-GCM 加密存储
- 主密码仅存储不可逆哈希
- 剪贴板密码 30 秒自动清除
- 支持恢复密钥找回
- 数据仅保存在本地 `%APPDATA%/PasswordManager/`

---

## English

A local-first, offline desktop password manager.

### Features

- 🔐 Master password encryption (PBKDF2 + AES-256-GCM)
- 📝 CRUD for password entries
- 📁 Group management (create, rename, delete)
- 🔍 Fast search with keyword highlighting
- 📋 One-click copy username/password/URL (auto-clear clipboard in 30s)
- 👁 Password show/hide toggle
- 📤 CSV plaintext export
- 🔑 Recovery key for master password reset
- 🔒 Lock function
- 🎨 Fluent Design style UI

### Tech Stack

- Python 3.12+
- PyQt5 (native, no additional UI framework)
- SQLite + AES-256-GCM encryption
- PyInstaller packaged as single exe (~40MB)

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python -m app.main
```

### Build

```bash
# Generate icon (first time)
python scripts/generate_icon.py

# Build exe
pyinstaller build.spec
```

### Security

- Master password derived via PBKDF2 (600,000 iterations)
- Sensitive fields encrypted with AES-256-GCM
- Master password stored as irreversible hash only
- Clipboard auto-cleared after 30 seconds
- Recovery key support
- Data stored locally only at `%APPDATA%/PasswordManager/`
