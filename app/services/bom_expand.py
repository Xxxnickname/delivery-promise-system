"""多级 BOM 展开、环检测、深度限制与一对一替代料折算。

本模块只使用 Decimal，不调用 LLM。展开结果按叶子物料合并，同一物料出现在
多条路径时累加总量，但每条路径单独保留，便于追溯和后续缺料解释。
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable, Mapping

from app.core.decimal_utils import round_qty
from app.models.domain import BomEdge, ExpansionResult, SubstitutionResult, SubstituteRule
from app.services.alias import normalize_item_code


class BomError(ValueError):
    """BOM 结构错误基类。"""


class BomCycleError(BomError):
    """检测到循环 BOM；错误消息中保留完整环路径。"""

    def __init__(self, path: list[str]) -> None:
        self.path = path
        super().__init__("BOM 存在循环：" + " > ".join(path))


class BomDepthError(BomError):
    """BOM 超过允许的最大层级。"""


def edges_from_records(records: Iterable[Mapping[str, object]]) -> list[BomEdge]:
    """把解析后的 BOM 记录转换成领域边对象。"""
    edges: list[BomEdge] = []
    for record in records:
        edges.append(
            BomEdge(
                parent_code=normalize_item_code(record["parent_code"]),
                child_code=normalize_item_code(record["child_code"]),
                qty_per=record["qty_per"],  # type: ignore[arg-type]
                scrap_rate=record.get("scrap_rate", Decimal("0")),  # type: ignore[arg-type]
                substitute_group=record.get("substitute_group"),  # type: ignore[arg-type]
                level=record.get("level"),  # type: ignore[arg-type]
            )
        )
    return edges


def _normalize_edge(edge: BomEdge) -> BomEdge:
    """统一料号大小写和空白，防止同一物料因文本差异重复计算。"""
    return BomEdge(
        parent_code=normalize_item_code(edge.parent_code),
        child_code=normalize_item_code(edge.child_code),
        qty_per=edge.qty_per,
        scrap_rate=edge.scrap_rate,
        substitute_group=edge.substitute_group,
        level=edge.level,
    )


def expand_bom(root_code: str, root_qty: Decimal, edges: Iterable[BomEdge], max_depth: int = 5) -> ExpansionResult:
    """从成品向下展开到叶子物料。

    参数：
    - root_code：成品/父件标准料号；
    - root_qty：订单数量；
    - edges：BOM 边集合；
    - max_depth：允许的最大父子层数，默认 5。

    返回：
    - requirements：叶子物料 -> 需求量；
    - traces：叶子物料 -> 所有 BOM 路径；
    - depth_used：实际达到的最大层级。

    异常：
    - BomCycleError：父子关系形成环；
    - BomDepthError：超过最大层级；
    - BomError：根节点没有 BOM 或数量非法。
    """
    root = normalize_item_code(root_code)
    if root_qty <= 0:
        raise BomError("订单数量必须大于 0")

    children: dict[str, list[BomEdge]] = defaultdict(list)
    for raw_edge in edges:
        edge = _normalize_edge(raw_edge)
        if edge.qty_per <= 0:
            raise BomError(f"BOM 用量必须大于 0：{edge.parent_code} > {edge.child_code}")
        if edge.scrap_rate < 0:
            raise BomError(f"损耗率不能为负数：{edge.parent_code} > {edge.child_code}")
        children[edge.parent_code].append(edge)

    if not children.get(root):
        raise BomError(f"找不到 {root} 的 BOM")

    requirements: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    traces: dict[str, list[str]] = defaultdict(list)
    depth_used = 0

    def visit(node: str, qty: Decimal, depth: int, path: list[str]) -> None:
        nonlocal depth_used
        depth_used = max(depth_used, depth)
        outgoing = children.get(node, [])
        if not outgoing:
            requirements[node] = round_qty(requirements[node] + qty)
            traces[node].append(" > ".join(path))
            return
        if depth >= max_depth:
            raise BomDepthError(f"BOM 超过 {max_depth} 层：{' > '.join(path)}")

        for edge in outgoing:
            if edge.child_code in path:
                raise BomCycleError(path + [edge.child_code])
            multiplier = edge.qty_per * (Decimal("1") + edge.scrap_rate)
            visit(edge.child_code, qty * multiplier, depth + 1, path + [edge.child_code])

    visit(root, root_qty, 0, [root])
    return ExpansionResult(root_code=root, root_qty=root_qty, requirements=dict(requirements), traces=dict(traces), depth_used=depth_used)


def plan_substitutions(
    requirements: Mapping[str, Decimal],
    available_primary: Mapping[str, Decimal],
    rules: Iterable[SubstituteRule],
    available_substitute: Mapping[str, Decimal] | None = None,
) -> list[SubstitutionResult]:
    """按一对一替代规则计算主料/替代料用量。

    替代比例定义：替代料需求 = 主料缺口 × ratio。
    若提供替代料可用量，则只分配实际可用量，并计算剩余缺口；否则按可采购替代料处理。
    """
    results: list[SubstitutionResult] = []
    for rule in rules:
        primary = normalize_item_code(rule.primary_code)
        substitute = normalize_item_code(rule.substitute_code)
        required = round_qty(requirements.get(primary, Decimal("0")))
        if required <= 0:
            continue
        primary_available = round_qty(available_primary.get(primary, Decimal("0")))
        primary_used = min(required, max(primary_available, Decimal("0")))
        missing = round_qty(required - primary_used)
        wanted_substitute = round_qty(missing * rule.ratio)
        if available_substitute is not None:
            substitute_available = round_qty(available_substitute.get(substitute, Decimal("0")))
            substitute_qty = min(wanted_substitute, max(substitute_available, Decimal("0")))
        else:
            substitute_qty = wanted_substitute
        covered_primary = round_qty(substitute_qty / rule.ratio) if rule.ratio > 0 else Decimal("0")
        remaining_gap = round_qty(max(Decimal("0"), missing - covered_primary))
        results.append(
            SubstitutionResult(
                primary_code=primary,
                substitute_code=substitute,
                group_code=rule.group_code,
                required_qty=required,
                available_primary=primary_available,
                primary_used=primary_used,
                substitute_qty=substitute_qty,
                remaining_gap=remaining_gap,
            )
        )
    return results

