"""Pure assessment calculations, independent of Django and storage."""
from decimal import Decimal, ROUND_HALF_UP


def aggregate_marks(components, marks):
    if not marks or not components:
        raise ValueError("Assessment components and examiner marks are required.")
    if any(len(row) != len(components) for row in marks):
        raise ValueError("Each examiner must score all components.")
    averages = []
    total = Decimal(0)
    for index, component in enumerate(components):
        average = sum(Decimal(row[index]) for row in marks) / len(marks)
        total += average
        averages.append({**component, "average": str(average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))})
    return {"components": averages, "overall": str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "examiner_count": len(marks)}
