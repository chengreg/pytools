# PyTools - Python 工具集合

这是一个Python工具集合，包含各种实用的文件处理工具。

## 工具列表

### 1. 批量重命名工具 (file_rename.py)

一个功能强大的批量重命名工具，可以去除文件名中指定的字符串，让文件名更加简洁。

#### 功能特点

- 🎯 **精确匹配**：精确匹配并移除指定的字符串
- 🔍 **预览模式**：支持 `--dry-run` 参数预览重命名效果
- 🛡️ **安全保护**：检查文件冲突，避免覆盖现有文件
- 📁 **智能处理**：只处理文件，跳过目录
- 🧹 **自动清理**：自动清理多余的空格和连字符
- ⚠️ **错误处理**：完善的错误处理和提示信息

#### 使用方法

```bash
# 方法1：命令行参数（推荐用于简单路径）
python file_rename.py /path/to/directory "要移除的字符串"

# 方法2：交互式模式（推荐用于复杂路径）
python file_rename.py --interactive
# 或者直接运行程序，会自动进入交互式模式
python file_rename.py

# 示例：将 "Unreal Engine 5 C++- Advanced Action RPG - Activate Ability By Tag.mp4" 
# 重命名为 "Activate Ability By Tag.mp4"
python file_rename.py /path/to/videos "Unreal Engine 5 C++- Advanced Action RPG - "

# 预览模式：查看将要进行的重命名操作，但不实际执行
python file_rename.py /path/to/directory "要移除的字符串" --dry-run
python file_rename.py --interactive --dry-run

# 在当前目录中移除字符串
python file_rename.py . "前缀字符串"
```

#### 解决路径空格问题

如果你的路径包含空格或特殊字符（如 `/Users/mac/Documents/教程/Advanced Action RPG/Enemy AI/`），建议使用交互式模式：

```bash
# 使用交互式模式，可以安全地输入包含空格的路径
python file_rename.py --interactive

# 或者直接运行程序
python file_rename.py
```

交互式模式会逐步引导你输入：
1. 目标目录路径（支持粘贴完整路径）
2. 要移除的字符串
3. 确认操作（提供预览模式建议）

#### 参数说明

- `directory`: 目标目录路径（可选，不提供时进入交互式模式）
- `remove_string`: 要从文件名中移除的字符串（可选，不提供时进入交互式模式）
- `--dry-run`: 预览模式，显示将要进行的操作但不实际执行
- `--interactive, -i`: 强制使用交互式模式
- `--verbose, -v`: 详细输出模式

#### 使用示例

假设你有一个包含以下文件的目录：
```
Unreal Engine 5 C++- Advanced Action RPG - Activate Ability By Tag.mp4
Unreal Engine 5 C++- Advanced Action RPG - Combat System.mp4
Unreal Engine 5 C++- Advanced Action RPG - Inventory Management.mp4
```

运行以下命令：
```bash
python file_rename.py /path/to/videos "Unreal Engine 5 C++- Advanced Action RPG - "
```

文件将被重命名为：
```
Activate Ability By Tag.mp4
Combat System.mp4
Inventory Management.mp4
```

#### 安全特性

- **预览模式**：使用 `--dry-run` 参数可以预览所有将要进行的重命名操作
- **冲突检测**：自动检测文件名冲突，避免覆盖现有文件
- **权限检查**：检查目录访问权限，提供清晰的错误信息
- **备份建议**：建议在执行批量操作前备份重要文件

### 2. 文件计数工具 (file_counter.py)

统计指定目录中各种类型文件的数量。

## 系统要求

- Python 3.6+
- 无需额外依赖包

## 安装

1. 克隆或下载此仓库
2. 确保Python环境已安装
3. 直接运行即可，无需安装

## 注意事项

⚠️ **重要提醒**：在执行批量重命名操作前，建议：
1. 使用 `--dry-run` 参数预览操作
2. 备份重要文件
3. 在测试目录中先试用

## 许可证

MIT License
