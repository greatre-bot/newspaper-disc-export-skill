# 国民日报旧报纸光盘整期 PDF 导出 Skill

这是 `newspaper-disc-export` Skill 的交接说明。它用于在 Windows 上只读检查旧报纸光盘，直接读取光盘内的原始版面图片，并按日期和版次顺序生成整期 PDF 及单张光盘的导出报告。

> **请勿将 Skill 内的 `SKILL.md` 改名为 `README.md`。**  
> `SKILL.md` 是 Codex 识别和调用 Skill 的正式入口；本文件是给使用者和其他 AI 阅读的安装、操作与维护说明。

## 1. 能做什么

- 只读扫描指定的 CD/DVD 光驱，不向光盘写入任何内容。
- 识别已验证的隐藏图片目录：`019Z\<8 个 U+007F 字符>\pic\YYYY\MM\DD\NN.jpg`。
- 将同一天的 `01.jpg、02.jpg……` 按数值顺序合成为一个整期 PDF。
- 保留原始像素尺寸、长宽比、DPI、横竖方向、边缘信息和 JPEG 压缩数据。
- 自动检查图片、PDF 页数、版次连续性、内嵌 JPEG 数据和已有输出。
- 支持先扫描、再导出一个样本、最后批量导出。
- 支持断点续跑：已经验证成功的 PDF 会跳过，不会覆盖。
- 每张光盘单独生成扫描结果、PDF 清单、失败清单和 Markdown 导出报告。

本 Skill 默认只生成：

```text
<项目根目录>\output\
├─ 01_整期PDF\
│  └─ YYYY\YYYY-MM\国民日报＊YYYY-MM-DD＊共XX版.pdf
└─ 99_目录与报告\
   ├─ <光盘名>扫描结果.json
   ├─ <光盘名>整期PDF清单.csv
   ├─ <光盘名>导出失败.csv
   └─ <光盘名>导出报告.md
```

Windows 文件名不能包含半角星号 `*`，所以文件名使用全角星号 `＊`。

## 2. 适用范围

这个 Skill 已针对前两张同系列“国民日报”光盘验证，可直接复用到目录结构和图片格式相同的后续光盘。

它不是只绑定某一张光盘：光驱盘符、项目目录、光盘名称和标签都是命令行参数。每张新光盘必须先执行只读预检，确认结构、日期范围、版数和现有日期冲突后才能批量导出。

如果新光盘出现以下情况，不要强行运行批量导出：

- 没有已知的 `019Z` 隐藏目录；
- 原始版面不是按 `YYYY\MM\DD\NN.jpg` 保存；
- 内容存放在 DAT、BIN、PAK、数据库或其他容器中；
- 相同日期已经存在但无法确认内容一致；
- 图片头、版次规则或报纸名称明显不同。

遇到这些变化时，应先做只读文件清单和格式分析，再修改适配脚本。不要启动 `autorun.exe`，也不要先采用界面截图。

## 3. 已知原始文件形式

前两张光盘的原始版面是一版一张 JPEG 图片，路径形式为：

```text
F:\019Z\<8 个 U+007F 字符>\pic\1928\09\01\01.jpg
F:\019Z\<8 个 U+007F 字符>\pic\1928\09\01\02.jpg
...
```

光盘软件只是读取这些图片；正常导出不需要运行光盘自带程序。

这批 JPEG 使用了特殊文件头：开头可能为 `FF D8 FF D9 FF D8 FF E0`。最前面的四字节构成一个空 JPEG，若原样嵌入 PDF，部分 PDF 解码器会显示空白页。本脚本只在写入 PDF 的数据流中去掉这四字节，不修改光盘文件，也不重新压缩图片像素。

## 4. 安全原则

1. 光盘始终只读，绝不在光驱中创建、修改、重命名或删除文件。
2. 不运行 `autorun.exe`。
3. 不用文件创建时间或修改时间猜测报纸日期。
4. 日期和版次必须按数值排序，不能出现第 01、10、02 版的顺序。
5. 已有且验证成功的 PDF 不覆盖；不一致的同名文件报告为冲突。
6. 保持图片原始比例和方向，不拉伸成 A4，不裁切正文或边缘。
7. 横向扫描页保持横向，不能为了观看方向而擅自旋转。
8. 批量运行前必须完成扫描预检和至少一个日期的样本检查。

## 5. 文件包结构

```text
README.md
newspaper-disc-export\
├─ SKILL.md
├─ agents\
│  └─ openai.yaml
├─ references\
│  └─ disc-format.md
└─ scripts\
   ├─ export_whole_pdf.py
   ├─ requirements.txt
   └─ setup.ps1
```

## 6. 安装给 Codex 使用

1. 解压交接包。
2. 将完整的 `newspaper-disc-export` 文件夹复制到：

   ```text
   C:\Users\<你的用户名>\.codex\skills\newspaper-disc-export
   ```

   也可以在 PowerShell 中使用环境变量所表示的位置：

   ```text
   %USERPROFILE%\.codex\skills\newspaper-disc-export
   ```

3. 保持文件夹名称和其中的 `SKILL.md` 不变。
4. 在 Codex 中新建一个任务，或重启 Codex 后再调用该 Skill。

建议直接把下面这段话交给 Codex，并按实际情况修改盘符、项目目录、光盘序号和标签：

```text
使用 $newspaper-disc-export 处理 F:\ 中的第三张光盘。
项目根目录是 D:\国民日报。
光盘名称是“第三张光盘”，标签是 gmrb3。
只生成整期 PDF 和本张光盘导出报告，继续按日期顺序保存到
output\01_整期PDF，不覆盖已经验证成功的 PDF。
先只读扫描并检查日期冲突，再导出最早日期作为样本；样本通过后完成整张光盘。
不要运行 autorun.exe，不要向 F:\ 写入任何内容。
```

Codex 应按以下顺序执行：只读检查光驱 → 扫描预检 → 阅读扫描 JSON → 导出一个日期样本 → 渲染检查 → 批量导出 → 检查失败清单和报告。

## 7. 不通过 Codex，直接在本机运行

以下命令均在 PowerShell 中执行。先设置三个路径；示例中的项目根目录可以换成自己的目录：

```powershell
$skill = "$env:USERPROFILE\.codex\skills\newspaper-disc-export"
$project = 'D:\国民日报'
$drive = 'F:\'
```

### 7.1 创建项目内的 Python 环境

```powershell
& "$skill\scripts\setup.ps1" -ProjectRoot $project
$python = Join-Path $project 'temp\newspaper-disc-export-runtime\.venv\Scripts\python.exe'
```

依赖只安装到项目的 `temp` 目录，不会全局修改系统 Python。

### 7.2 只读扫描，不导出 PDF

```powershell
& $python "$skill\scripts\export_whole_pdf.py" `
  --project-root $project `
  --drive $drive `
  --disc-name '第三张光盘' `
  --disc-label 'gmrb3' `
  --scan-only
```

执行后先打开：

```text
<项目根目录>\output\99_目录与报告\第三张光盘扫描结果.json
```

确认日期范围、日期数量、总图片数、缺失版次、日历空缺、横向图片和已有日期冲突。

### 7.3 导出一个日期作为样本

把日期换成扫描结果中实际存在的最早日期：

```powershell
& $python "$skill\scripts\export_whole_pdf.py" `
  --project-root $project `
  --drive $drive `
  --disc-name '第三张光盘' `
  --disc-label 'gmrb3' `
  --sample-date 'YYYY-MM-DD'
```

检查样本 PDF 的第一页、最后一页；如果扫描结果中有横向图片，还要检查一个包含横向页的日期。确认正文完整、页序正确、没有白页、没有裁边或拉伸。

### 7.4 批量导出整张光盘

样本通过后，去掉 `--scan-only` 和 `--sample-date`：

```powershell
& $python "$skill\scripts\export_whole_pdf.py" `
  --project-root $project `
  --drive $drive `
  --disc-name '第三张光盘' `
  --disc-label 'gmrb3'
```

中断后可以再次执行同一命令。脚本会验证并跳过已经成功生成的 PDF。

如果已经通过其他方法找到了图片根目录，也可以明确传入：

```powershell
--source-root 'F:\实际图片根目录'
```

## 8. 如何手动查看隐藏图片目录

已验证光盘的隐藏目录名包含 8 个不可见的 U+007F 字符，资源管理器即使开启“显示隐藏项目”也不便直接输入。可以用 PowerShell 只读打开：

```powershell
$hidden = 'F:\019Z\' + ([string][char]127 * 8)
$pic = Join-Path $hidden 'pic'
Get-ChildItem -LiteralPath $pic -Force
explorer.exe $pic
```

查看某个日期的图片：

```powershell
$dateDir = Join-Path $pic '1928\09\01'
Get-ChildItem -LiteralPath $dateDir -Filter '*.jpg' |
  Sort-Object { [int]$_.BaseName }
```

如果需要复制出来人工检查，请复制到硬盘上的新目录，不要对光盘文件执行移动、改名或删除操作。

## 9. 完成后的质量检查

每张光盘至少确认：

- 扫描预检没有未解决的日期冲突；
- 导出的 PDF 数量等于扫描发现的日期数量；
- 每份 PDF 页数等于该日期发现的版面数；
- 版次从 01 开始按数值连续排列，缺版已在报告中列出；
- PDF 可以打开，第一页、最后一页和横向页显示正常；
- 没有白页、黑页、裁边、强制旋转或比例拉伸；
- `导出失败.csv` 只有表头，没有失败记录；
- 输出目录中没有残留的 `.partial` 文件；
- 已有 PDF 被验证后跳过，没有被重复覆盖；
- 本张光盘的 Markdown 导出报告已生成。

有些 Windows 版 Poppler 不能正确处理带中文的文件路径。遇到渲染失败时，只为视觉检查把样本 PDF 复制到纯英文临时路径后渲染，最终 PDF 仍保留在规定的中文输出目录。

## 10. 常见问题

### PDF 是空白页，但 JPEG 能打开

不要用未处理文件头的简单图片转 PDF 命令。使用本 Skill 自带的 `export_whole_pdf.py`，它会对已知的双 JPEG 起始标记做无损兼容处理。

### 找不到隐藏目录

先确认光驱盘符和光盘是否可读，再用只读方式递归列出文件。不要运行 `autorun.exe`。如果确实不是已知结构，应暂停批量导出，分析图片、索引、数据库或数据包。

### 报告存在缺失日期

缺失的日历日期只表示光盘源中没有对应目录，不能自动断定为漏刊。报告应如实保留，但不要凭空补日期。

### 同一天已经有 PDF

脚本会验证成功文件并跳过；如果验证不通过或内容不一致，会报告冲突。不要直接覆盖，先查明它属于哪一张光盘以及版面是否一致。

### 会不会消耗大量 Codex token

图片检查和 PDF 合并由本地 Python 脚本完成，不会按每一页调用模型。Codex 的指令理解、检查和总结仍会消耗正常对话 token。Skill 安装好后，也可以完全退出 Codex，直接用本 README 中的 PowerShell 命令在本机运行。

## 11. 已验证结果

该流程已在同系列第二张光盘上完整验证：

- 光盘标签：`gmrb2`
- 日期范围：1928-09-01 至 1929-01-31
- 实际日期：145 天
- 原始版面：1686 张
- 缺失版次：0
- 主要尺寸：竖版 2336×3307；横版 3304×2336 或 3307×2336
- 已验证扫描、样本导出、整盘导出、横向页面、断点跳过、PDF 页数和内嵌 JPEG 数据一致性

这些数据只是对已处理光盘的验证记录，不能用来预设下一张光盘的日期范围或版数；新光盘仍必须先扫描。

## 12. 给接手者的最短操作路线

1. 把 `newspaper-disc-export` 文件夹放进 `%USERPROFILE%\.codex\skills\`。
2. 插入新光盘，确认实际盘符。
3. 在 Codex 新任务中使用第 6 节的提示词。
4. 等 Codex 完成只读预检并核对扫描结果。
5. 检查一个样本日期。
6. 样本正常后批量导出。
7. 最后检查 `01_整期PDF` 和本张光盘的导出报告。

只要光盘仍是相同的数据结构，整个过程不需要打开光盘自带软件，也不需要逐张截图或手工打印。
