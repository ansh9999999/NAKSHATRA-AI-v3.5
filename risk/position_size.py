def calculate_position_size(
    capital,
    risk_percent,
    entry_price,
    stop_loss_price
):

    risk_amount = capital * (risk_percent / 100)

    stop_distance = abs(entry_price - stop_loss_price)

    if stop_distance == 0:
        return 0

    quantity = risk_amount / stop_distance

    return round(quantity, 4)
