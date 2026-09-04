from __future__ import annotations
from utils import magic_tables

def get_rook_attacks(square: int, global_occupancy: int) -> int:
    mask = magic_tables.ROOK_MASKS[square]
    magic = magic_tables.ROOK_MAGICS[square]
    shift = magic_tables.ROOK_SHIFTS[square]
    offset = magic_tables.ROOK_OFFSETS[square]
    
    blockers = global_occupancy & mask
    magic_idx = ((blockers * magic) & 0xFFFFFFFFFFFFFFFF) >> shift
    return magic_tables.ROOK_LOOKUP_POOL[offset + magic_idx]

def get_bishop_attacks(square: int, global_occupancy: int) -> int:
    mask = magic_tables.BISHOP_MASKS[square]
    magic = magic_tables.BISHOP_MAGICS[square]
    shift = magic_tables.BISHOP_SHIFTS[square]
    offset = magic_tables.BISHOP_OFFSETS[square]
    
    blockers = global_occupancy & mask
    magic_idx = ((blockers * magic) & 0xFFFFFFFFFFFFFFFF) >> shift
    return magic_tables.BISHOP_LOOKUP_POOL[offset + magic_idx]