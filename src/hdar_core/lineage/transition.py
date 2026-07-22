def verify_epoch_advancement(parent_epoch: int, current_epoch: int) -> bool:
    return current_epoch == parent_epoch + 1
