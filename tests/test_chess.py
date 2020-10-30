"""Test the chess logic."""
import collections
import datetime
import typing

from server import enums, models

from .utils import ModelTest


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

INITIAL_LAYOUT = {}
for _file, _piece in enumerate('RNBQKBNR'):
    INITIAL_LAYOUT[0, _file] = _piece
    INITIAL_LAYOUT[1, _file] = 'P'
    INITIAL_LAYOUT[6, _file] = 'p'
    INITIAL_LAYOUT[7, _file] = _piece.lower()


class TestChess(ModelTest):
    """Test the chess logic."""

    def setUp(self):
        """Create a game for testing."""
        super().setUp()
        self.user_1 = models.User.create(
            username='Test', password='password', _email='email'
        )
        self.user_2 = models.User.create(
            username='Test2', password='password', _email='email2'
        )
        self.game = models.Game.create(
            host=self.user_1, away=self.user_2, mode=enums.Mode.CHESS,
            main_thinking_time=datetime.timedelta(days=1),
            fixed_extra_time=datetime.timedelta(0),
            time_increment_per_turn=datetime.timedelta(minutes=1),
            started_at=datetime.datetime.now()
        )

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

    def _test_make_move(
            self, layout: typing.Dict[typing.Tuple[int, int], str],
            move: Move, expected_valid: bool = True):
        """Test validation of some move."""
        # Lay out the board.
        for rank, file in layout:
            symbol = layout[(rank, file)]
            piece_type = PIECES[symbol[0].lower()]
            side = enums.Side.HOST if symbol[0].isupper() else enums.Side.AWAY
            models.Piece.create(
                rank=rank, file=file, piece_type=piece_type, side=side,
                game=self.game, has_moved='x' in symbol,
                first_move_last_turn='y' in symbol
            )
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

    def test_board_layout(self):
        """Check that the board is initially laid out correctly."""
        self.game.game_mode.layout_board()
        self.assert_layout(INITIAL_LAYOUT)

    def test_off_board(self):
        """Test trying to move a piece off the board."""
        self._test_make_move(
            INITIAL_LAYOUT, Move(
                start_rank=0, start_file=0, end_rank=0, end_file=-1,
                promotion=None
            ), expected_valid=False
        )

    def test_no_move(self):
        """Test making a move to the same square."""
        self._test_make_move(
            INITIAL_LAYOUT, Move(
                start_rank=1, start_file=3, end_rank=1, end_file=3,
                promotion=None
            ), expected_valid=False
        )

    def test_move_opponent(self):
        """Test trying to move a piece belonging to the opponent."""
        self._test_make_move(
            INITIAL_LAYOUT, Move(
                start_rank=6, start_file=4, end_rank=5, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_move_empty(self):
        """Test trying to move a non-existant piece."""
        self._test_make_move(
            INITIAL_LAYOUT, Move(
                start_rank=3, start_file=4, end_rank=3, end_file=6,
                promotion=None
            ), expected_valid=False
        )

    def test_move_through(self):
        """Test trying to move a bishop through another piece."""
        self._test_make_move(
            INITIAL_LAYOUT, Move(
                start_rank=0, start_file=2, end_rank=2, end_file=4,
                promotion=None
            ), expected_valid=False
        )

    def test_take_own(self):
        """Test trying to take our own piece."""
        self._test_make_move(
            INITIAL_LAYOUT, Move(
                start_rank=0, start_file=0, end_rank=0, end_file=1,
                promotion=None
            ), expected_valid=False
        )

    def test_diagonal_rook(self):
        """Test trying to move a rook diagonally."""
        self._test_make_move(
            {(0, 0): 'R'}, Move(
                start_rank=0, start_file=0, end_rank=1, end_file=1,
                promotion=None
            ), expected_valid=False
        )

    def test_straight_bishop(self):
        """Test trying to move a bishop in a straight line."""
        self._test_make_move(
            {(3, 1): 'B'}, Move(
                start_rank=3, start_file=1, end_rank=7, end_file=1,
                promotion=None
            ), expected_valid=False
        )

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
