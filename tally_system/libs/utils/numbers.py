def rounded_safe_div_percent(numerator, denominator, precision=2, default=100):
    return round(100 * (numerator / denominator) if denominator else 100, 2)
