"""订单解释文案：只基于中间结果，不生成任何新数字。"""
from __future__ import annotations

from app.models.domain import OrderPromise


def explain_order(promise: OrderPromise) -> str:
    """根据承诺状态生成自然语言解释。

    约束：文案中不出现具体数量、日期和天数，避免模型/模板改写时篡改计算结果；
    所有数字仍由结构化接口字段承载。
    """
    if promise.can_commit:
        return "根据当前BOM展开与供给冲减结果，订单所需物料已齐套，可按客户交期安排生产。"
    if promise.kit_date is None:
        return "订单存在尚未覆盖的物料缺口，当前无法确定齐套日期。建议优先补充短缺物料，并复核在途与替代料方案。"
    return "订单物料齐套日期晚于客户交期，主要受短缺物料供给影响。建议优先处理高风险物料，并评估替代料、加急采购或调整承诺日期。"
