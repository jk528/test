#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻联播六要素 AI API 自动填写脚本

功能：
  读取 Phase 1 生成的六要素数据源 JSON，
  调用外部 AI API（OpenAI 兼容接口）自动填写六要素，
  保存为六要素结果 JSON 供 Phase 3 合并。

支持的外部 AI API（不消耗 TeleAgent 积分）：
  - DeepSeek（推荐，性价比最高）：api_base_url=https://api.deepseek.com/v1, model=deepseek-chat
  - 通义千问：api_base_url=https://dashscope.aliyuncs.com/compatible-mode/v1, model=qwen-plus
  - Moonshot/Kimi：api_base_url=https://api.moonshot.cn/v1, model=moonshot-v1-8k
  - 本地 Ollama：api_base_url=http://localhost:11434/v1, model=qwen2.5:14b
  - 任何 OpenAI 兼容接口

用法：
  python fill_elements_api.py 20260915
  python fill_elements_api.py 20260915 --config ../自动化任务/config/config.json
  python fill_elements_api.py 20260915 --api-key xxx --base-url https://api.deepseek.com/v1 --model deepseek-chat

配置优先级（从高到低）：
  1. 命令行参数
  2. 环境变量（XWLB_AI_API_KEY / XWLB_AI_BASE_URL / XWLB_AI_MODEL）
  3. config.json 中的 modes.ai_api 配置
  4. 默认值（DeepSeek）

版本：v1.0.0（2026-09-16）
"""

import sys
import os
import re
import json
import time
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime, date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ============================================================
# 配置读取
# ============================================================
def load_config(config_path):
    """从 config.json 读取 AI API 配置"""
    if not config_path or not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        ai_config = config.get("modes", {}).get("ai_api", {})
        return ai_config
    except Exception as e:
        logger.warning(f"读取配置文件失败: {e}")
        return {}


def resolve_api_settings(args, config_path):
    """
    解析 API 配置，优先级：命令行 > 环境变量 > config.json > 默认值
    """
    ai_config = load_config(config_path)

    api_key = (
        args.api_key
        or os.environ.get("XWLB_AI_API_KEY")
        or ai_config.get("api_key", "")
    )

    base_url = (
        args.base_url
        or os.environ.get("XWLB_AI_BASE_URL")
        or ai_config.get("api_base_url", "")
        or "https://api.deepseek.com/v1"
    )

    model = (
        args.model
        or os.environ.get("XWLB_AI_MODEL")
        or ai_config.get("api_model", "")
        or "deepseek-chat"
    )

    # 确保 base_url 不以 / 结尾
    base_url = base_url.rstrip("/")

    if not api_key:
        logger.error(
            "未找到 API Key。请通过以下方式之一配置：\n"
            "  1. 命令行参数: --api-key YOUR_KEY\n"
            "  2. 环境变量: set XWLB_AI_API_KEY=YOUR_KEY\n"
            "  3. config.json: modes.ai_api.api_key"
        )
        sys.exit(1)

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "max_tokens": ai_config.get("max_tokens", 4096),
        "temperature": ai_config.get("temperature", 0.3),
    }


# ============================================================
# 路径计算
# ============================================================
def get_archive_paths(date_str):
    """计算归档目录和相关文件路径"""
    target_date = datetime.strptime(date_str, "%Y%m%d").date()
    year_month = f"{target_date.year}年{target_date.month}月"
    archive_dir = os.path.join(BASE_DIR, "归档", year_month)

    return {
        "archive_dir": archive_dir,
        "datasource_json": os.path.join(archive_dir, f"六要素数据源_{date_str}.json"),
        "result_json": os.path.join(archive_dir, f"六要素结果_{date_str}.json"),
        "report_md": os.path.join(archive_dir, f"新闻联播总结_{date_str}.md"),
    }


# ============================================================
# 构建系统提示词
# ============================================================
SYSTEM_PROMPT = """你是新闻联播总结报告的六要素提取助手。你的任务是根据新闻标题和摘要，为每条新闻提取五要素信息。

## 五要素定义

1. **location**（地点）：新闻发生的主要地点。如"北京"、"全国"、"福建漳州"、"也门"。无明确值填"—"。
2. **subject**（新闻主体）：新闻的核心行动者或主体。
   - 人物：用 `<u>` 占位符标记，如 `<u>国家主席</u>`、`<u>美国总统</u>`、`<u>国务院总理</u>`
   - 机构：直接填写机构名称，不加下划线，如"国家统计局"、"工业和信息化部"、"农业农村部"
   - 事件核心对象：不加下划线，如"也门冲突双方"、"俄乌冲突双方"
   - 无明确主体填"—"
3. **event**（事件）：核心事件的简短描述。如"会见卡塔尔首相"、"发布8月经济数据"、"印发发展规划"。
4. **cause**（原因/目的）：新闻的原因或目的。如"推动数字贸易发展"、"改善农村生产生活条件"。无则填"—"。
5. **method**（方式/手段）：事件的方式或手段。如"在京会见"、"新闻发布会发布数据"、"印发发展规划"、"举办论坛"。

## 特殊规则

1. **完整版行**（is_placeholder=true）：固定填写 location="全国", subject="—", event="当日全部新闻汇总", cause="—", method="完整播报"
2. **快讯目录行**（title含"联播快讯"且无子条目标记）：固定填写 location="—", subject="—", event="播报XX联播快讯", cause="—", method="目录播报"
3. **人物脱敏**：标题中已用 `<u>` 标签包裹的人物占位符（如 `<u>国家主席</u>`），在 subject 字段中保持同样格式。
4. **机构不加下划线**：机构名称直接填写，不加 `<u>` 标签。
5. **禁止大量填"—"**：每条新闻都应尽量提取实质内容，不要轻易填"—"。
6. **简洁准确**：每个字段控制在20字以内，确保信息准确、表述简洁。

## 输出格式

返回 JSON 数组，每个元素包含 `idx` 和 `elements` 字段：

```json
[
  {
    "idx": "完整版",
    "elements": {
      "location": "全国",
      "subject": "—",
      "event": "当日全部新闻汇总",
      "cause": "—",
      "method": "完整播报"
    }
  },
  {
    "idx": "1",
    "elements": {
      "location": "福建漳州",
      "subject": "<u>国家主席</u>",
      "event": "给福建省'漳州110'全体队员回信勉励",
      "cause": "勉励公安干警坚守为民初心、担当奉献",
      "method": "回信勉励"
    }
  }
]
```

注意：只返回 JSON 数组，不要包含任何其他文字、解释或 markdown 代码块标记。"""


# ============================================================
# 构建用户消息
# ============================================================
def build_user_message(datasource):
    """构建用户消息，包含所有待填写的新闻条目"""
    items_to_fill = []
    for item in datasource.get("news_items", []):
        entry = {
            "idx": item["idx"],
            "title": item["title"],
            "category": item.get("category", ""),
            "is_placeholder": item.get("is_placeholder", False),
        }
        if item.get("summary"):
            entry["summary"] = item["summary"]
        if item.get("full_text"):
            entry["full_text"] = item["full_text"]
        if item.get("importance"):
            entry["importance"] = item["importance"]
        items_to_fill.append(entry)

    msg = f"以下是 {datasource.get('date_display', '')} 新闻联播的 {len(items_to_fill)} 条新闻数据。\n"
    msg += "请为每条新闻提取五要素，按 idx 对应填写。\n\n"
    msg += json.dumps(items_to_fill, ensure_ascii=False, indent=2)
    return msg


# ============================================================
# 调用 AI API
# ============================================================
def call_ai_api(settings, system_prompt, user_message, max_retries=3):
    """
    调用 OpenAI 兼容的 Chat Completions API（使用标准库 urllib）
    """
    url = f"{settings['base_url']}/chat/completions"
    payload_dict = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": settings.get("temperature", 0.3),
        "max_tokens": settings.get("max_tokens", 4096),
        "response_format": {"type": "json_object"},
    }

    use_response_format = True

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"调用 AI API (尝试 {attempt}/{max_retries}): "
                f"model={settings['model']}, base_url={settings['base_url']}"
            )

            # 如果上一次因 response_format 失败，则去掉
            if not use_response_format:
                payload_dict.pop("response_format", None)

            payload = json.dumps(payload_dict).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings['api_key']}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content = resp_data["choices"][0]["message"]["content"]
                logger.info(f"API 返回内容长度: {len(content)} 字符")
                return content

        except urllib.error.HTTPError as e:
            status_code = e.code
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")[:500]
            except Exception:
                pass
            logger.warning(f"API 请求失败 (HTTP {status_code}): {error_body}")

            # 如果是 response_format 不支持导致的 400 错误，去掉 response_format 重试
            if status_code == 400 and "response_format" in str(error_body):
                logger.info("检测到 response_format 不支持，移除该参数后重试...")
                use_response_format = False
                payload_dict.pop("response_format", None)
                continue

            if attempt < max_retries:
                wait = min(5 * attempt, 30)
                logger.info(f"等待 {wait} 秒后重试...")
                time.sleep(wait)
            else:
                raise

        except Exception as e:
            logger.warning(f"API 调用异常: {e}")
            if attempt < max_retries:
                wait = min(5 * attempt, 30)
                logger.info(f"等待 {wait} 秒后重试...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("API 调用失败，已达最大重试次数")


# ============================================================
# 解析 AI 返回的 JSON
# ============================================================
def parse_ai_response(content):
    """
    解析 AI 返回的 JSON 内容，兼容多种格式：
    - 纯 JSON 数组
    - JSON 对象包含数组
    - markdown 代码块包裹的 JSON
    """
    # 去除可能的 markdown 代码块标记
    content = content.strip()
    if content.startswith("```"):
        # 去除 ```json 或 ``` 标记
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
    content = content.strip()

    # 尝试直接解析
    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            # 可能是 {"news_items": [...]} 或 {"results": [...]} 等格式
            for key in ["news_items", "results", "items", "data"]:
                if key in result and isinstance(result[key], list):
                    return result[key]
            # 单个对象
            if "idx" in result and "elements" in result:
                return [result]
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 数组部分
    array_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group())
        except json.JSONDecodeError:
            pass

    # 尝试逐行提取
    items = []
    idx_pattern = re.compile(r'"idx"\s*:\s*"([^"]*)"')
    elements_pattern = re.compile(
        r'"elements"\s*:\s*\{([^}]*)\}', re.DOTALL
    )
    for idx_match in idx_pattern.finditer(content):
        idx = idx_match.group(1)
        # 在 idx 后面找 elements
        after = content[idx_match.end():]
        elem_match = elements_pattern.search(after)
        if elem_match:
            elem_text = "{" + elem_match.group(1) + "}"
            try:
                elements = json.loads(elem_text)
                items.append({"idx": idx, "elements": elements})
            except json.JSONDecodeError:
                pass

    if items:
        return items

    logger.error(f"无法解析 AI 返回的 JSON: {content[:500]}")
    raise ValueError("AI 返回内容无法解析为 JSON")


# ============================================================
 # 合并六要素到数据源
# ============================================================
def merge_elements(datasource, ai_results):
    """将 AI 填写的六要素合并回数据源结构"""
    # 建立 idx -> elements 映射
    elements_map = {}
    for item in ai_results:
        idx = item.get("idx", "")
        elements = item.get("elements", {})
        if idx and elements:
            elements_map[idx] = elements

    # 填充数据源中的每条新闻
    filled_count = 0
    for item in datasource.get("news_items", []):
        idx = item.get("idx", "")
        if idx in elements_map:
            item["elements"] = elements_map[idx]
            filled_count += 1
        elif item.get("is_placeholder"):
            # 完整版固定值
            item["elements"] = {
                "location": "全国",
                "subject": "—",
                "event": "当日全部新闻汇总",
                "cause": "—",
                "method": "完整播报",
            }
            filled_count += 1

    logger.info(f"已填写 {filled_count}/{len(datasource.get('news_items', []))} 条新闻的六要素")
    return datasource


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="新闻联播六要素 AI API 自动填写",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "使用示例：\n"
            "  python fill_elements_api.py 20260915\n"
            "  python fill_elements_api.py 20260915 --config ../自动化任务/config/config.json\n"
            "  python fill_elements_api.py 20260915 --api-key sk-xxx --base-url https://api.deepseek.com/v1 --model deepseek-chat\n"
        ),
    )
    parser.add_argument("date", nargs="?", default=None, help="目标日期 YYYYMMDD")
    parser.add_argument("--config", default=None, help="config.json 路径")
    parser.add_argument("--api-key", default=None, help="AI API Key")
    parser.add_argument("--base-url", default=None, help="AI API Base URL")
    parser.add_argument("--model", default=None, help="AI 模型名称")
    parser.add_argument("--force", action="store_true", help="强制重新生成（覆盖已有结果）")
    args = parser.parse_args()

    # 日期处理
    if args.date:
        if not re.match(r"^\d{8}$", args.date):
            logger.error("日期格式错误，应为 YYYYMMDD")
            sys.exit(1)
        date_str = args.date
    else:
        yesterday = date.today() - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")

    # 计算路径
    paths = get_archive_paths(date_str)

    # 检查数据源 JSON 是否存在
    if not os.path.exists(paths["datasource_json"]):
        logger.error(f"六要素数据源 JSON 不存在: {paths['datasource_json']}")
        logger.error("请先运行 Phase 1: python gen_report_final.py <date>")
        sys.exit(1)

    # 检查是否已有结果 JSON
    if os.path.exists(paths["result_json"]) and not args.force:
        logger.info(f"六要素结果已存在: {paths['result_json']}")
        logger.info("如需重新生成，请使用 --force 参数")
        # 验证已有结果的完整性
        try:
            with open(paths["result_json"], "r", encoding="utf-8") as f:
                existing = json.load(f)
            filled = sum(
                1 for it in existing.get("news_items", [])
                if it.get("elements") is not None
            )
            total = len(existing.get("news_items", []))
            logger.info(f"已有结果: {filled}/{total} 条已填写")
            if filled == total:
                logger.info("已有结果完整，直接使用")
                sys.exit(0)
        except Exception:
            logger.warning("已有结果文件损坏，将重新生成")

    # 读取数据源
    logger.info(f"读取数据源: {paths['datasource_json']}")
    with open(paths["datasource_json"], "r", encoding="utf-8") as f:
        datasource = json.load(f)

    total_items = len(datasource.get("news_items", []))
    logger.info(f"数据源包含 {total_items} 条新闻")

    # 解析 API 配置
    config_path = args.config or os.path.join(
        SCRIPT_DIR, "..", "自动化任务", "config", "config.json"
    )
    config_path = os.path.normpath(config_path)
    settings = resolve_api_settings(args, config_path)

    logger.info(f"API 配置: model={settings['model']}, base_url={settings['base_url']}")

    # 构建消息
    user_message = build_user_message(datasource)
    logger.info(f"用户消息长度: {len(user_message)} 字符")

    # 调用 AI API
    try:
        content = call_ai_api(settings, SYSTEM_PROMPT, user_message)
    except Exception as e:
        logger.error(f"AI API 调用失败: {e}")
        sys.exit(1)

    # 解析返回结果
    try:
        ai_results = parse_ai_response(content)
        logger.info(f"解析到 {len(ai_results)} 条六要素结果")
    except Exception as e:
        logger.error(f"解析 AI 返回结果失败: {e}")
        sys.exit(1)

    # 合并六要素
    result = merge_elements(datasource, ai_results)

    # 验证填写完整性
    filled_count = sum(
        1 for it in result.get("news_items", [])
        if it.get("elements") is not None
    )
    if filled_count < total_items:
        logger.warning(
            f"填写不完整: {filled_count}/{total_items}，缺失的条目将使用默认值"
        )
        # 为未填写的条目设置默认值
        for item in result.get("news_items", []):
            if item.get("elements") is None:
                is_brief = "联播快讯" in item.get("title", "")
                if item.get("is_placeholder"):
                    item["elements"] = {
                        "location": "全国",
                        "subject": "—",
                        "event": "当日全部新闻汇总",
                        "cause": "—",
                        "method": "完整播报",
                    }
                elif is_brief:
                    item["elements"] = {
                        "location": "—",
                        "subject": "—",
                        "event": f"播报{item['title']}",
                        "cause": "—",
                        "method": "目录播报",
                    }
                else:
                    item["elements"] = {
                        "location": "—",
                        "subject": "—",
                        "event": item.get("title", "")[:20],
                        "cause": "—",
                        "method": "—",
                    }

    # 保存结果
    logger.info(f"保存结果: {paths['result_json']}")
    with open(paths["result_json"], "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"六要素填写完成: {paths['result_json']}")
    logger.info(f"  总条目: {total_items}")
    logger.info(f"  AI填写: {filled_count}")
    logger.info(f"  默认值: {total_items - filled_count}")

    print(f"\n{'='*60}")
    print("AI API 六要素填写完成！")
    print(f"{'='*60}")
    print(f"结果文件: {paths['result_json']}")
    print(f"填写率: {filled_count}/{total_items} ({filled_count*100//total_items}%)")
    print(f"下一步: python gen_report_final.py {date_str} --merge")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
