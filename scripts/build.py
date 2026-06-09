#!/usr/bin/env python3
"""
HXnote LaTeX 条件编译脚本
============================

根据命令行参数决定是否渲染章导览 (\\chapterintro) 和章末复习题 (\\section{复习题})。

用法:
    python build.py ../note/grade4/社会医学.tex                    # 全部渲染（默认）
    python build.py ../note/grade4/社会医学.tex --no-intro          # 不渲染章导览
    python build.py ../note/grade4/社会医学.tex --no-review         # 不渲染复习题
    python build.py ../note/grade4/社会医学.tex --no-intro --no-review  # 两者都不渲染
    python build.py ../note/grade4/社会医学.tex --clean             # 仅清理辅助文件

原理:
    - 章导览：通过 LaTeX 布尔开关 \\ifrenderchapterintro 控制（hxnotebook.sty 已内置）
    - 复习题：新章节文件使用 \\reviewcontent{...} 包裹 → LaTeX 开关控制
              旧章节文件 → Python 预处理，注释掉复习题段落
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="HXnote LaTeX 条件编译脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "main_tex",
        help="主 .tex 文件路径（如 ../note/grade4/社会医学.tex）",
    )
    parser.add_argument(
        "--no-intro",
        action="store_true",
        help="不渲染各章的 \\chapterintro 导览框",
    )
    parser.add_argument(
        "--no-review",
        action="store_true",
        help="不渲染各章末的复习题（选择题/名词解释/简答题/参考答案）",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="仅清理辅助文件（.aux .log .toc .out 等），不编译",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="编译输出目录（默认为主 .tex 所在目录）",
    )
    return parser.parse_args()


def clean_aux_files(tex_dir: Path):
    """清理 LaTeX 辅助文件"""
    extensions = [".aux", ".log", ".toc", ".out", ".synctex.gz", ".thm"]
    removed = []
    for ext in extensions:
        for f in tex_dir.glob(f"*{ext}"):
            f.unlink()
            removed.append(f.name)
    if removed:
        print(f"[clean] 已删除: {', '.join(removed)}")
    else:
        print("[clean] 没有需要清理的辅助文件")


def find_chapter_files(main_tex_path: Path) -> list[Path]:
    """从主 tex 文件中解析出所有 \\input 的章节文件路径"""
    content = main_tex_path.read_text(encoding="utf-8")
    chapter_files = []
    for match in re.finditer(r"\\input\{([^}]+)\}", content):
        rel_path = match.group(1)
        # 相对于主 tex 所在目录
        abs_path = (main_tex_path.parent / rel_path).resolve()
        if abs_path.exists():
            chapter_files.append(abs_path)
    return chapter_files


def patch_main_tex(main_tex_path: Path, no_intro: bool, no_review: bool, tmp_dir: Path) -> Path:
    """
    生成修改后的主 tex 文件（到临时目录），设置条件渲染开关。

    修复 \\input@path 以包含原始目录，确保 sty 文件能被找到。
    返回修改后的文件路径。
    """
    content = main_tex_path.read_text(encoding="utf-8")

    # 修复 \input@path：只搜索当前目录（所有依赖文件已复制到 tmp_dir）
    for i, line in enumerate(content.split("\n")):
        if r"\def\input@path" in line:
            content = content.replace(line, r"\def\input@path{{./}}")
            break

    # 在 \begin{document} 之前插入开关设置
    flags = []
    if no_intro:
        flags.append("\\renderchapterintrofalse")
    if no_review:
        flags.append("\\renderreviewfalse")

    if flags:
        flag_block = "% ===== 条件编译开关（由 build.py 自动生成） =====\n" + "\n".join(flags) + "\n"
        if "\\begin{document}" in content:
            content = content.replace("\\begin{document}", flag_block + "\\begin{document}")
        else:
            print("[warning] 未找到 \\begin{document}，开关设置可能无效")

    tmp_main = tmp_dir / main_tex_path.name
    tmp_main.write_text(content, encoding="utf-8")
    return tmp_main


def remove_review_sections_from_content(content: str, fname: str) -> str:
    """
    预处理章节内容：移除复习题部分。

    识别以 \\section{复习题} 开头到文件末尾的全部内容，将其注释掉。
    返回修改后的内容。
    """
    pattern = re.compile(r"^(\s*\\section\{复习题\}.*)$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        pattern2 = re.compile(r"^(\s*% -----.*复习题.*-----\s*\n\s*\\section\{复习题\}.*)$", re.MULTILINE)
        match = pattern2.search(content)
    if not match:
        return content  # 没有复习题段落，返回原内容

    start_pos = match.start()
    after_review = content[start_pos:]

    commented = "\n% ===== 以下复习题内容由 build.py --no-review 自动注释 =====\n"
    for line in after_review.split("\n"):
        if line.strip():
            commented += "% " + line + "\n"
        else:
            commented += "%\n"

    print(f"  [no-review] 已注释复习题: {fname}")
    return content[:start_pos] + commented


def prepare_chapters(main_tex_path: Path, no_review: bool, tmp_dir: Path) -> set[str]:
    """
    准备章节文件：如果 --no-review，对旧风格章节文件做预处理。

    在 tmp_dir 中保留原始子目录结构（如 营养chapters/）。
    返回已处理的绝对路径集合（这些文件已写入 tmp_dir，无需再复制）。
    """
    handled: set[str] = set()
    if not no_review:
        return handled

    chapter_files = find_chapter_files(main_tex_path)
    for ch_path in chapter_files:
        content = ch_path.read_text(encoding="utf-8")
        if r"\reviewcontent" in content:
            continue  # 新风格：LaTeX 开关自动处理
        modified = remove_review_sections_from_content(content, ch_path.name)
        if modified != content:
            # 有修改，写入 tmp_dir 保持子目录结构
            rel_path = ch_path.relative_to(main_tex_path.parent)
            target = tmp_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(modified, encoding="utf-8")
            handled.add(str(ch_path.resolve()))
    return handled


def run_xelatex(tex_path: Path, output_dir: Path, n_runs: int = 2) -> bool:
    """运行 xelatex 编译"""
    tex_path = tex_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / f"{tex_path.stem}.log"

    for i in range(n_runs):
        print(f"  [xelatex] 第 {i+1}/{n_runs} 次编译...")
        result = subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                f"-output-directory={output_dir}",
                str(tex_path),
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(tex_path.parent),
        )
        stdout = result.stdout or ""
        # 检查是否有严重错误
        if "Fatal error" in stdout or "Emergency stop" in stdout:
            print(f"[error] 编译失败！详见 {log_file}")
            lines = stdout.split("\n")
            for line in lines[-40:]:
                if line.strip():
                    print(f"  {line}")
            return False

    pdf_path = output_dir / f"{tex_path.stem}.pdf"
    if pdf_path.exists():
        print(f"  [done] PDF 已生成: {pdf_path}")
        return True
    else:
        print(f"[error] PDF 未生成，请检查 {log_file}")
        return False


def main():
    args = parse_args()
    main_tex = Path(args.main_tex).resolve()

    if not main_tex.exists():
        print(f"[error] 文件不存在: {main_tex}")
        sys.exit(1)

    tex_dir = main_tex.parent
    output_dir = Path(args.output_dir).resolve() if args.output_dir else tex_dir

    # --clean 模式
    if args.clean:
        clean_aux_files(tex_dir)
        return

    # 检查是否有任何开关被触发
    needs_patching = args.no_intro or args.no_review

    if not needs_patching:
        # 简单模式：直接编译
        print(f"[build] 完整模式编译: {main_tex.name}")
        success = run_xelatex(main_tex, output_dir)
        sys.exit(0 if success else 1)

    # 条件编译模式
    flags_desc = []
    if args.no_intro:
        flags_desc.append("无章导览")
    if args.no_review:
        flags_desc.append("无复习题")
    print(f"[build] 条件编译 ({', '.join(flags_desc)}): {main_tex.name}")

    with tempfile.TemporaryDirectory(prefix="hxnote_build_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        # Step 1: 预处理章节文件（针对旧风格的 --no-review）
        # 处理后直接写入 tmp_dir 中的对应子目录
        print("[build] 准备章节文件...")
        handled = prepare_chapters(main_tex, args.no_review, tmp_dir)

        # Step 2: 将未修改的章节文件复制到临时目录（保持子目录结构）
        chapter_files = find_chapter_files(main_tex)
        for ch_path in chapter_files:
            if str(ch_path.resolve()) in handled:
                continue
            rel_path = ch_path.relative_to(main_tex.parent)
            target = tmp_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ch_path, target)

        # Step 3: 复制 hxnotebook.sty 到临时目录
        sty_file = main_tex.parent.parent / "hxnotebook.sty"
        if sty_file.exists():
            shutil.copy2(sty_file, tmp_dir / "hxnotebook.sty")

        # Step 4: 生成带开关设置的主 tex（含 \input@path 修复）
        print("[build] 生成编译配置...")
        tmp_main = patch_main_tex(main_tex, args.no_intro, args.no_review, tmp_dir)

        # Step 5: 编译
        print("[build] 开始编译...")
        success = run_xelatex(tmp_main, output_dir)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
