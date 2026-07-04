# CNC CAM 与 G代码仿真分析软件

工程应用型 CNC CAM 与 G代码二维仿真桌面软件。当前支持 DXF 图纸预览、G代码解析、G0/G1/G2/G3 二维仿真、DXF 到基础 CAM G代码生成、车削/铣削模式、坐标归零、LINE 轮廓合并、中文图表显示和彩蛋按钮。

## 环境要求

- Python 3.11+
- PySide6
- matplotlib
- numpy
- ezdxf
- pyinstaller

## 运行源码版本

```powershell
py -m pip install -r requirements.txt
py main.py
```

程序启动时会先显示密码对话框。默认演示密码：

```text
tmxj
```

如果本机 `python` 命令已正确指向 Python 3.11+，也可以使用：

```powershell
python main.py
```

## 当前功能

- 默认车削模式，DXF 横向 X 映射为车床 Z，DXF 纵向 Y 按半径换算为车床 X 直径，程序头使用 `G18`
- 铣削模式保持 DXF X/Y 到 G代码 X/Y 的平面映射，程序头使用 `G17`
- 车削仿真画布按回转体截面显示：横轴为 Z，纵轴为半径 R，并镜像出中心线下半轮廓
- 圆弧输出支持 `折线近似` 和 `G2/G3 圆弧`
- G2/G3 支持 I/J 或 I/K 圆心偏移仿真
- 坐标归零可将 DXF 最小 X/Y 平移到工件零点
- 二维画布支持鼠标滚轮缩放、鼠标拖拽平移、双击适配视图
- 彩蛋按钮可播放 `assets/` 或工作目录下的图片和音频

## 打包 EXE

命令行运行：

```powershell
.\build_exe.bat
```

或直接双击 `build_exe.bat`。

打包完成后目标文件为：

```text
dist/CNC_CAM_Simulator/CNC_CAM_Simulator.exe
```

## 运行 EXE

```powershell
.\dist\CNC_CAM_Simulator\CNC_CAM_Simulator.exe
```

打包脚本会把以下目录加入程序资源：

```text
assets/
examples/
```

源码运行和 EXE 运行都通过 `core/resource_utils.py` 中的 `resource_path()` 查找资源；EXE 环境下兼容 `sys._MEIPASS`。

## 常见问题

1. PySide6 未安装  
   执行 `py -m pip install -r requirements.txt`。

2. 打包后资源找不到  
   确认使用 `build_exe.bat` 打包，并检查脚本中包含 `--add-data "assets;assets"` 和 `--add-data "examples;examples"`。

3. matplotlib 中文字体异常  
   软件会优先检测 `Microsoft YaHei`、`SimHei`、`SimSun`、`Noto Sans CJK SC`。如果系统没有中文字体，请安装其中一种。

4. EXE 启动慢  
   PySide6、matplotlib 和 Qt 多媒体组件体积较大，首次启动较慢属于正常现象。当前使用文件夹版打包，通常比 onefile 更稳定。

5. Windows Defender 误报  
   课程设计本地打包的 EXE 可能因未签名被提示风险。建议保留源码和打包脚本，必要时在受信任环境中重新打包。
