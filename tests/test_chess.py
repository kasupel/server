"""Test the chess logic."""
import collections
import typing

from server import enums, models

from .utils import GameTest


PIECES = {
    'p': enums.PieceType.PAWN,
    'r': enums.PieceType.ROOK,
    'n': enums.PieceType.KNIGHT,
    'b': enums.PieceType.BISHOP,
    'q': enums.PieceType.QUEEN,
    'k': enums.PieceType.KING
}

Move = collections.namedtuple('Move', [
    'start_rank', 'start_file', 'end_rank', 'end_file', 'promotion'
])


class ChessTest(GameTest):
    """Test class with utility functions for testing chess."""

    def assert_layout(
            self, layout: typing.Dict[typing.Tuple[int, int], str],
            rest_empty: bool = True):
        """Check that the board is laid out in a certain way."""
        for rank in range(8):
            for file in range(8):
                if ((rank, file) not in layout) and (not rest_empty):
                    continue
                symbol = layout.get((rank, file), None)
                expected_type = PIECES[symbol.lower()] if symbol else None
                piece = models.Piece.get_or_none(
                    models.Piece.file == file, models.Piece.rank == rank,
                    models.Piece.game == self.game
                )
                actual_type = piece.piece_type if piece else None
                self.assertEqual(expected_type, actual_type)

    def make_layout(self, layout: typing.Dict[typing.Tuple[int, int], str]):
        """Lay out the board in some way."""
        for rank, file in layout:
            symbol = layout[(rank, file)]
            piece_type = PIECES[symbol[0].lower()]
            side = enums.Side.HOST if symbol[0].isupper() else enums.Side.AWAY
            models.Piece.create(
                rank=rank, file=file, piece_type=piece_type, side=side,
                game=self.game, has_moved='x' in symbol,
                first_move_last_turn='y' in symbol
            )

    def assert_moves(
            self, layout: typing.Dict[typing.Tuple[int, int], str],
            moves: typing.Tuple[typing.Tuple[int, int]],
            host_turn: bool = True):
        """Check that the allowed moves are correct."""
        if not host_turn:
            self.game.current_turn = enums.Side.AWAY
        self.make_layout(layout)
        actual_moves = self.game.game_mode.possible_moves(
            self.game.current_turn
        )
        expected_moves = []
        for move in moves:
            if len(move) == 4:
                move = (*move, None)    # Add promotion.
            expected_moves.append(move)
        self.assertEqual(set(actual_moves), set(expected_moves))

    def _test_make_move(
            self, layout: typing.Dict[typing.Tuple[int, int], str],
            move: Move, expected_valid: bool = True, host_turn: bool = True):
        """Test validation of some move."""
        if not host_turn:
            self.game.current_turn = enums.Side.AWAY
        self.make_layout(layout)
        # Try to make the move.
        actual_valid = self.game.game_mode.make_move(
            start_rank=move.start_rank, start_file=move.start_file,
            end_rank=move.end_rank, end_file=move.end_file,
            promotion=move.promotion.value if move.promotion else None
        )
        self.assertEqual(actual_valid, expected_valid)
        # Make sure the end position is correct.
        if not expected_valid:
            return
        moved_piece = layout[(move.start_rank, move.start_file)]
        if move.promotion:
            for piece_symbol in PIECES:
                if PIECES[piece_symbol] == move.promotion:
                    symbol = piece_symbol
            if self.game.current_turn == enums.Side.HOST:
                moved_piece = symbol.upper()
        layout[(move.start_rank, move.start_file)] = moved_piece
        del layout[(move.start_rank, move.start_file)]
        self.assert_layout(layout)


class TestChessRooks(ChessTest):
    """Tests specific to rook movement."""

    def test_diagonal_rook(self):
        """Test trying to move a rook diagonally."""
        self._test_make_move(
            {(0, 0): 'R'}, Move(
                start_rank=0, start_file=0, end_rank=1, end_file=1,
                promotion=None
            ), expected_valid=False
        )

    def test_promote_rook(self):
        """Test trying to promote a rook."""
        self._test_make_move(
            {(6, 4): 'R'}, Move(
                start_rank=6, start_file=4, end_rank=7, end_file=4,
                promotion=enums.PieceType.QUEEN
            ), expected_valid=False
        )

    def test_rook_take_own(self):
        """Test trying to take our own piece with a rook."""
        self._test_make_move(
            {(3, 2): 'R', (5, 2): 'P'}, Move(
                start_rank=3, start_file=2, end_rank=5, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_rook_move_through(self):
        """Test trying to move a rook through another piece."""
        self._test_make_move(
            {(4, 1): 'R', (4, 3): 'k'}, Move(
                start_rank=4, start_file=1, end_rank=4, end_file=5,
                promotion=None
            ), expected_valid=False
        )


class TestChessBishops(ChessTest):
    """Tests specific to bishops."""

    def test_straight_bishop(self):
        """Test trying to move a bishop in a straight line."""
        self._test_make_move(
            {(3, 1): 'B'}, Move(
                start_rank=3, start_file=1, end_rank=7, end_file=1,
                promotion=None
            ), expected_valid=False
        )

    def test_promote_bishop(self):
        """Test trying to promote a rook."""
        self._test_make_move(
            {(5, 2): 'B'}, Move(
                start_rank=5, start_file=2, end_rank=7, end_file=0,
                promotion=enums.PieceType.QUEEN
            ), expected_valid=False
        )

    def test_bishop_take_own(self):
        """Test trying to take our own piece with a bishop."""
        self._test_make_move(
            {(0, 0): 'B', (5, 5): 'Q'}, Move(
                start_rank=0, start_file=0, end_rank=5, end_file=5,
                promotion=None
            ), expected_valid=False
        )

    def test_bishop_move_through(self):
        """Test trying to move a bishop through another piece."""
        self._test_make_move(
            {(0, 2): 'B', (1, 3): 'P'}, Move(
                start_rank=0, start_file=2, end_rank=2, end_file=4,
                promotion=None
            ), expected_valid=False
        )


class TestChessPawns(ChessTest):
    """Tests specific to pawn movement."""

    def test_pawn_sideways(self):
        """Test trying to move a pawn right 2."""
        self._test_make_move(
            {(2, 7): 'P'}, Move(
                start_rank=2, start_file=7, end_rank=2, end_file=5,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_sideways_knight_move(self):
        """Test trying to move a pawn left 2 forward 1."""
        self._test_make_move(
            {(2, 7): 'P'}, Move(
                start_rank=2, start_file=7, end_rank=3, end_file=5,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_forward_knight_move(self):
        """Test trying to move a pawn left 1 forward 2."""
        self._test_make_move(
            {(2, 7): 'P'}, Move(
                start_rank=2, start_file=7, end_rank=4, end_file=6,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_late_double_move(self):
        """Test trying to move a moved pawn two ranks."""
        self._test_make_move(
            {(3, 7): 'Px'}, Move(
                start_rank=3, start_file=7, end_rank=5, end_file=7,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_diagonal_no_take(self):
        """Test trying to move a pawn diagonally without taking."""
        self._test_make_move(
            {(2, 4): 'P'}, Move(
                start_rank=2, start_file=4, end_rank=3, end_file=5,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_take_own(self):
        """Test trying to take our own piece with a pawn."""
        self._test_make_move(
            {(1, 3): 'P', (2, 4): 'B'}, Move(
                start_rank=1, start_file=3, end_rank=2, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_into_piece(self):
        """Test moving a pawn forward into our own piece."""
        self._test_make_move(
            {(3, 3): 'P', (4, 3): 'R'}, Move(
                start_rank=3, start_file=3, end_rank=4, end_file=3,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_take_forwards(self):
        """Test trying to take forwards with a pawn."""
        self._test_make_move(
            {(1, 6): 'P', (2, 6): 'q'}, Move(
                start_rank=1, start_file=6, end_rank=2, end_file=6,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_no_promote(self):
        """Test moving a pawn to the final rank without promoting."""
        self._test_make_move(
            {(6, 2): 'P'}, Move(
                start_rank=6, start_file=2, end_rank=7, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_promote_to_king(self):
        """Test trying to promote a pawn to a king."""
        self._test_make_move(
            {(6, 1): 'P'}, Move(
                start_rank=6, start_file=1, end_rank=7, end_file=1,
                promotion=enums.PieceType.KING
            ), expected_valid=False
        )

    def test_pawn_early_promote(self):
        """Test trying to promote a pawn before it reaches the final rank."""
        self._test_make_move(
            {(5, 1): 'P'}, Move(
                start_rank=5, start_file=1, end_rank=6, end_file=1,
                promotion=enums.PieceType.QUEEN
            ), expected_valid=False
        )

    def test_pawn_far_forward(self):
        """Test trying to move a pawn 4 squares forward."""
        self._test_make_move(
            {(1, 4): 'P'}, Move(
                start_rank=1, start_file=4, end_rank=5, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_backward(self):
        """Test trying to move a pawn backward."""
        self._test_make_move(
            {(1, 4): 'P'}, Move(
                start_rank=4, start_file=2, end_rank=3, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_pawn_hop_piece(self):
        """Test trying to double move a pawn forward over another piece."""
        self._test_make_move(
            {(1, 3): 'P', (2, 3): 'N'}, Move(
                start_rank=1, start_file=3, end_rank=3, end_file=3,
                promotion=None
            ), expected_valid=False
        )


class TestChessKnights(ChessTest):
    """Tests specific to knight movement."""

    def test_knight_straight(self):
        """Test trying to move a knight in a straight line."""
        self._test_make_move(
            {(3, 4): 'N'}, Move(
                start_rank=3, start_file=4, end_rank=5, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_knight_diagonal(self):
        """Test trying to move a knight to a diagonally adjacent square."""
        self._test_make_move(
            {(2, 6): 'N'}, Move(
                start_rank=2, start_file=6, end_rank=3, end_file=5,
                promotion=None
            ), expected_valid=False
        )

    def test_knight_long(self):
        """Test trying to move a knight down 3 right 1."""
        self._test_make_move(
            {(3, 4): 'N'}, Move(
                start_rank=4, start_file=3, end_rank=1, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_knight_take_own(self):
        """Test trying to take our own piece with a knight."""
        self._test_make_move(
            {(0, 1): 'N', (2, 2): 'P'}, Move(
                start_rank=0, start_file=1, end_rank=2, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_promote_knight(self):
        """Test trying to promote a knight."""
        self._test_make_move(
            {(6, 4): 'N'}, Move(
                start_rank=6, start_file=4, end_rank=7, end_file=6,
                promotion=enums.PieceType.QUEEN
            ), expected_valid=False
        )


class TestChessKings(ChessTest):
    """Tests specific to king movement and castling."""

    def test_promote_king(self):
        """Test trying to promote a king."""
        self._test_make_move(
            {(6, 1): 'K'}, Move(
                start_rank=6, start_file=1, end_rank=7, end_file=2,
                promotion=enums.PieceType.ROOK
            ), expected_valid=False
        )

    def test_king_take_own(self):
        """Test trying to take our own piece with a king."""
        self._test_make_move(
            {(3, 4): 'K', (3, 5): 'N'}, Move(
                start_rank=3, start_file=4, end_rank=3, end_file=5,
                promotion=None
            ), expected_valid=False
        )

    def test_king_move_far(self):
        """Test trying to move a king two squares."""
        self._test_make_move(
            {(0, 0): 'K'}, Move(
                start_rank=0, start_file=0, end_rank=2, end_file=0,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_moved_king(self):
        """Test trying to castle with a moved king."""
        self._test_make_move(
            {(0, 0): 'R', (0, 4): 'Kx'}, Move(
                start_rank=0, start_file=4, end_rank=0, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_moved_rook(self):
        """Test trying to castle with a moved rook."""
        self._test_make_move(
            {(0, 4): 'K', (0, 7): 'Rx'}, Move(
                start_rank=0, start_file=4, end_rank=0, end_file=6,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_too_far(self):
        """Test trying to castle too far to the left."""
        self._test_make_move(
            {(0, 4): 'K', (0, 0): 'R'}, Move(
                start_rank=0, start_file=4, end_rank=0, end_file=1,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_no_rook(self):
        """Test trying to castle with a non-existant rook."""
        self._test_make_move(
            {(0, 4): 'K'}, Move(
                start_rank=0, start_file=4, end_rank=0, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_through_piece(self):
        """Test trying to castle through another piece."""
        self._test_make_move(
            {(0, 4): 'K', (0, 1): 'N', (0, 0): 'R'}, Move(
                start_rank=0, start_file=4, end_rank=0, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_out_of_check(self):
        """Test trying to castle out of check."""
        self._test_make_move(
            {(0, 4): 'K', (3, 4): 'r', (0, 7): 'R'}, Move(
                start_rank=0, start_file=4, end_rank=0, end_file=6,
                promotion=None
            ), expected_valid=False
        )

    def test_castle_through_check(self):
        """Test trying to castle through check."""
        self._test_make_move(
            {(7, 4): 'k', (6, 4): 'B', (7, 7): 'r'}, Move(
                start_rank=7, start_file=4, end_rank=7, end_file=6,
                promotion=None
            ), expected_valid=False, host_turn=False
        )


class TestChessQueens(ChessTest):
    """Tests specific to queen movement."""

    def test_queen_knights_move(self):
        """Test trying to move a queen in a knight's move."""
        self._test_make_move(
            {(2, 6): 'Q'}, Move(
                start_rank=2, start_file=6, end_rank=0, end_file=7,
                promotion=None
            ), expected_valid=False
        )

    def test_promote_queen(self):
        """Test trying to promote a queen."""
        self._test_make_move(
            {(0, 2): 'Q'}, Move(
                start_rank=0, start_file=2, end_rank=7, end_file=2,
                promotion=enums.PieceType.ROOK
            ), expected_valid=False
        )

    def test_queen_take_own(self):
        """Test trying to take our own piece with a queen."""
        self._test_make_move(
            {(4, 4): 'Q', (7, 7): 'N'}, Move(
                start_rank=4, start_file=4, end_rank=7, end_file=7,
                promotion=None
            ), expected_valid=False
        )

    def test_queen_move_through(self):
        """Test trying to move a queen through another piece."""
        self._test_make_move(
            {(0, 3): 'Q', (1, 3): 'p'}, Move(
                start_rank=0, start_file=3, end_rank=5, end_file=3,
                promotion=None
            ), expected_valid=False
        )


class TestChess(
        TestChessPawns, TestChessRooks, TestChessKnights, TestChessBishops,
        TestChessQueens, TestChessKings):
    """Collate all chess tests and add some non-piece-specific ones."""

    def test_board_layout(self):
        """Check that the board is initially laid out correctly."""
        self.game.game_mode.layout_board()
        layout = {}
        for file, piece in enumerate('RNBQKBNR'):
            layout[0, file] = piece
            layout[1, file] = 'P'
            layout[6, file] = 'p'
            layout[7, file] = piece.lower()
        self.assert_layout(layout)

    def test_off_board(self):
        """Test trying to move a piece off the board."""
        self._test_make_move(
            {(3, 0): 'R'}, Move(
                start_rank=3, start_file=0, end_rank=8, end_file=0,
                promotion=None
            ), expected_valid=False
        )

    def test_no_move(self):
        """Test making a move to the same square."""
        self._test_make_move(
            {(3, 2): 'K'}, Move(
                start_rank=3, start_file=2, end_rank=3, end_file=2,
                promotion=None
            ), expected_valid=False
        )

    def test_move_opponent(self):
        """Test trying to move a piece belonging to the opponent."""
        self._test_make_move(
            {(6, 4): 'p'}, Move(
                start_rank=6, start_file=4, end_rank=5, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_move_empty(self):
        """Test trying to move a non-existant piece."""
        self._test_make_move(
            {}, Move(
                start_rank=3, start_file=4, end_rank=3, end_file=6,
                promotion=None
            ), expected_valid=False
        )
