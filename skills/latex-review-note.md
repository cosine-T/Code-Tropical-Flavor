# LaTeX 复习笔记生成 Skill

## 概述

根据课程大纲（.doc）、授课PPT（.pptx）、往届笔记（.pdf）等多种参考资料，生成结构化的 LaTeX 复习笔记。输出一份主 `.tex` 文件 + 若干章节 `.tex` 文件，使用 `hxnotebook.sty` 样式包，通过 xelatex 编译为 PDF。

---

## 一、工作流程

### 步骤1：收集和整理参考资料

在 `note/grade4/` 下建立 `XX参考/` 文件夹，放入：

| 文件类型 | 说明 | 用途 |
|---------|------|------|
| `大纲.doc` | 本学年课程教学大纲（.doc 格式） | 确定章节框架、重难点划分 |
| `*.pptx` | 教师授课PPT（每个章节/主题一个文件） | 知识点详细内容 |
| `往年资料.pdf` / `往届笔记.pdf` | 往届复习笔记或参考资料 | 补充知识点、参考题型 |

### 步骤2：提取大纲内容

```bash
cd "note/grade4/XX参考"
python3 -c "
import olefile
ole = olefile.OleFileIO('大纲.doc')
wd = ole.openstream('WordDocument').read()
text = wd.decode('utf-16-le', errors='ignore')
print(text)
"
```

从大纲中提取：
- **章节列表**：确定笔记的章节目录
- **重点标记**：
  - 双下划线 = **掌握内容** → 用 `\keybox`（红色框）
  - 单下划线 = **熟悉内容** → 正文重点描述
  - 句尾 `*` = **教学难点** → 在章节导览和正文中标注

### 步骤3：提取PPT内容

```python
from pptx import Presentation

prs = Presentation("xxx.pptx")
for slide in prs.slides:
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                text = para.text.strip()
                if text and len(text) > 2:
                    print(text)
```

### 步骤4：提取PDF内容

```python
from PyPDF2 import PdfReader

reader = PdfReader("往届笔记.pdf")
for page in reader.pages:
    text = page.extract_text()
    if text:
        print(text)
```

### 步骤5：确定章节结构

以**教学大纲框架**为准，PPT内容为填充。大纲中有而PPT中缺失的内容，参考PDF补充。

### 步骤6：创建目录结构

```
note/grade4/
├── XX复习笔记.tex        # 主文件
├── XXchapters/            # 章节文件夹（中文名）
│   ├── ch01-绪论.tex
│   ├── ch02-xxx.tex
│   └── ...
└── XX参考/                # 参考资料文件夹
    ├── 大纲.doc
    ├── *.pptx
    └── 往年资料.pdf
```

---

## 二、主文件模板

```latex
\makeatletter
\def\input@path{{../}{./}}
\makeatother
\documentclass[10pt,a4paper,oneside]{ctexbook}
\RequirePackage{xcolor}
\definecolor{main}{RGB}{R,G,B}      % 科目主题色
\definecolor{light}{RGB}{R,G,B}     % 浅色背景

\usepackage{hxnotebook}

\begin{document}

% cover
\makecover
  {科目全称}
  {华西大纲·PPT·往年资料整理}
  {复习笔记}
  {\today}
  {greedyCat}

% ===== Table of Contents =====
\tableofcontents

% ===== 使用说明 =====
\chapter*{使用说明}
\addcontentsline{toc}{chapter}{使用说明}

\begin{itemize}[leftmargin=*]
    \item 本复习笔记严格依照《XXX》教学大纲章节编排...
    \item 各章末附有复习题（名词解释、简答题）...
    \item \textbf{\color{keyred}红色框}标识的内容为必须重点掌握的核心知识（对应大纲双下划线内容）。
    \item \textbf{\color{main}主题框}为概念释义，帮助理解专业术语。
    \item \textbf{\color{darkgreen}绿色提示框}为要点提示与补充说明。
    \item \textbf{\color{orange}橙色考点框}为常见考点与易考内容。
    \item 大纲中\textbf{句尾"*"标识}为教学难点，笔记中已特别标注。
\end{itemize}

\vspace{1cm}
\begin{center}
\begin{tcolorbox}[colback=yellow!10, colframe=yellow!80!black, boxrule=0.8pt, arc=6pt, width=0.85\textwidth, breakable]
\textbf{考核形式提示：}
\begin{itemize}[leftmargin=*]
    \item 平时考核成绩 50\% + 期末理论考核 50\%
    \item 考试范围：以教学大纲和教师课堂讲授内容为主
    \item 大纲双下划线内容 = 掌握内容（本笔记已用红色框标注）
    \item 大纲单下划线内容 = 熟悉内容
    \item 大纲句尾"*" = 教学难点
\end{itemize}
\end{tcolorbox}
\end{center}

\newpage

% =====================================================================
%  导入各章
% =====================================================================

\input{XXchapters/ch01-绪论.tex}
\input{XXchapters/ch02-xxx.tex}
% ...

\end{document}
```

### 颜色方案

每门科目使用**不同的 main 颜色**以便区分：

| 科目 | main RGB | light RGB | 色调 |
|------|----------|-----------|------|
| 环境卫生学 | `{0,82,136}` | `{230,240,250}` | 蓝色系 |
| 职业卫生 | `{160,100,20}` | `{255,248,230}` | 琥珀色系 |
| 社会医学 | `{0,105,92}` | `{230,245,238}` | 青绿色系 |
| 儿少卫生 | `{102,51,153}` | `{245,240,252}` | 紫罗兰色系 |

---

## 三、章节文件模板

```latex
% =====================================================================
%  CHAPTER X: 章节名
% =====================================================================
\chapter{章节名}
\setcounter{chapter}{X}
\chapterintro{
掌握...；熟悉...；了解...。（一句话概述本章学习目标）
}

% ----- X.1 第一节 -----
\section{第一节名}

% 概念定义框（主题色）
\begin{defbox}
\textbf{概念名}定义内容...
\end{defbox}

% 重点掌握框（红色）
\begin{keybox}
重点掌握的核心知识...
\end{keybox}

% 要点提示框（绿色）
\begin{tipbox}
补充说明和提示...
\end{tipbox}

% 常见考点框（橙色）
\begin{exambox}
常考知识点...
\end{exambox}

% ----- 复习题 -----
\section{复习题}

\begin{enumerate}[leftmargin=*, itemsep=8pt]
    \item \textbf{【名词解释】}术语1；术语2
    \item \textbf{【简答题】}简述XXXX。
\end{enumerate}

\subsection*{参考答案要点}

\begin{enumerate}[leftmargin=*, itemsep=5pt]
    \item 答案要点...
\end{enumerate}

\newpage
```

---

## 四、hxnotebook.sty 提供的命令和环境

### 文本标记命令

| 命令 | 效果 | 用途 |
|------|------|------|
| `\keyword{文字}` | 红色加粗 | 标记关键术语 |
| `\imp{文字}` | 主题色加粗 | 标记重要知识点 |
| `\seeref{label}` | 生成"详见第X节" | 交叉引用 |

### 彩色文本框环境

| 环境 | 边框色 | 背景色 | 前缀标签 | 用途 |
|------|--------|--------|----------|------|
| `keybox` | 红色 (keyred) | 浅红 (warnbg) | `! 重点掌握：` | 大纲双下划线内容 |
| `defbox` | 主题色 (main) | 浅色 (light) | `[概念] 概念释义：` | 专业术语定义 |
| `tipbox` | 深绿 (darkgreen) | 灰色 (graybg) | `[提示] 要点提示：` | 补充说明、背景知识 |
| `exambox` | 橙色 (orange) | 黄色调 | `[考点] 常见考点：` | 考试重点、高频考点 |

### 章节导览

```latex
\chapterintro{本章学习目标概述...}
```
生成主题色背景的章节导览框。

### 封面

```latex
\makecover{科目名}{副标题}{文档类型}{\today}{作者名}
```

### 其他

- 页眉自动显示当前章名，右侧显示"代号：热带风味"
- 背景水印 "By greedyCat"
- 章节标题自动编号和格式化
- `table[H]` 用于非浮动表格（不可在 box 内使用 `[htbp]`）

---

## 五、编译

### 编译器

**必须使用 xelatex**（pdflatex 不支持中文文件名路径）：

```bash
cd "note/grade4"
xelatex -interaction=nonstopmode -output-directory=. "XX复习笔记.tex"
# 运行两次以解析交叉引用
xelatex -interaction=nonstopmode -output-directory=. "XX复习笔记.tex"
```

### 常见编译问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `Float(s) lost` | `\begin{table}[htbp]` 在 tcolorbox 内 | 改为 `\begin{table}[H]` |
| `Text line contains an invalid character` | Unicode 字符损坏（如 ≈ 变 BEL） | 用 Python 二进制修复 |
| 中文文件名 `\input` 失败 | 用了 pdflatex | 改用 xelatex |
| `Missing character` | 字体缺失 Unicode 字符 | 替换为 LaTeX 命令（如 ①→(1), ≈→$\approx$） |

---

## 六、内容组织原则

1. **框架优先**：以教学大纲的章节目录为骨架，不随意增删章节
2. **重难点突出**：
   - 大纲双下划线内容 → `\keybox`（红色框）+ `\keyword{}`
   - 大纲单下划线内容 → `\imp{}` + 正文详述
   - 大纲 `*` 难点 → 章节导览中注明 + 正文特别标注"（教学难点*）"
3. **分层清晰**：概念→机制→影响因素→防控/应用，由浅入深
4. **表格优先**：对比性内容用 `\begin{table}[H]` + `\begin{tabularx}{\textwidth}{...}`
5. **每章附题**：名词解释 + 简答题 + 参考答案要点，覆盖该章核心知识点
6. **多源融合**：大纲定框架，PPT定内容，PDF补充缺漏
