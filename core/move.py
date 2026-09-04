import core.types

FROM_MASK = 0x3F          # 6 bits
TO_MASK = 0xFC0           # bits 6-11
FLAGS_MASK = 0xF000       # bits 12-15
PROMO_MASK = 0xF0000      # bits 16-19

def encode_move(from_sq, to_sq, flags=0, promotion=0):
    return (from_sq | (to_sq << 6) | (flags << 12) | (promotion << 16))

def get_from(move):
    return move & 0x3F

def get_to(move):
    return (move >> 6) & 0x3F

def get_flags(move):
    return (move >> 12) & 0xF

def get_promotion(move):
    return (move >> 16) & 0xF

def square_name(square: int) -> str:
	file = square % 8
	rank = square // 8
	return f"{core.types.FILES[file]}{rank + 1}"

def square_index(name: str) -> int:
	if len(name) != 2:
		raise ValueError(f"Invalid square name: {name!r}")

	file = ord(name[0].lower()) - ord('a')
	rank = ord(name[1]) - ord('1')

	if not (0 <= file < 8 and 0 <= rank < 8):
		raise ValueError(f"Invalid square name: {name!r}")

	return rank * 8 + file

def from_uci(uci: str) -> int:
	if len(uci) not in (4, 5):
		raise ValueError(f"Invalid UCI move: {uci!r}")

	from_sq = square_index(uci[:2])
	to_sq = square_index(uci[2:4])

	promotion = None
	if len(uci) == 5:
		promotion = uci[4].lower()

	promotion_map = {
		'q': core.types.PROMO_QUEEN,
		'r': core.types.PROMO_ROOK,
		'b': core.types.PROMO_BISHOP,
		'n': core.types.PROMO_KNIGHT
	}

	return encode_move(from_sq, to_sq, promotion=promotion_map.get(promotion, 0))

def to_uci(move: int) -> str:
	from_sq = get_from(move)
	to_sq = get_to(move)
	promotion = (move >> 16) & 0xF
	promotion_chars = {core.types.PROMO_QUEEN: 'q', core.types.PROMO_ROOK: 'r', core.types.PROMO_BISHOP: 'b', core.types.PROMO_KNIGHT: 'n'}
	move_str = f"{square_name(from_sq)}{square_name(to_sq)}"
	if promotion != 0:
		move_str += promotion_chars.get(promotion, '')
	return move_str
