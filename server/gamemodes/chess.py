"""The chess gamemode."""
from __future__ import annotations

import typing

from . import gamemode
from .. import enums, models, utils


class MockPiece:
    """A piece used for hypothetical moves, to avoid editing the DB."""

    def __init__(
            self, base: models.Piece, rank: int, file: int,
            p_type: enums.PieceType):
        """Create the mock piece."""
        self.rank = rank
        self.file = file
        self.piece_type = p_type
        self.side = base.side
        self.has_moved = True
        self.first_move_last_turn = not base.has_moved


class Chess(gamemode.GameMode):
    """A gamemode for chess."""

    def __init__(self, game: models.Game):
        """Store the game we are interested in."""
        self.hypothetical_moves = None
        super().__init__(game)

    def layout_board(self):
        """Put the pieces on the board."""
        p = enums.PieceType
        back_row = [
            p.ROOK, p.KNIGHT, p.BISHOP, p.QUEEN, p.KING, p.BISHOP, p.KNIGHT,
            p.ROOK
        ]
        for file, piece_type in enumerate(back_row):
            models.Piece.create(
                piece_type=piece_type, rank=0, file=file,
                side=enums.Side.HOST, game=self.game
            )
            models.Piece.create(
                piece_type=piece_type, rank=7, file=file,
                side=enums.Side.AWAY, game=self.game
            )
        for file in range(8):
            models.Piece.create(
                piece_type=p.PAWN, rank=1, file=file, side=enums.Side.HOST,
                game=self.game
            )
            models.Piece.create(
                piece_type=p.PAWN, rank=6, file=file, side=enums.Side.AWAY,
                game=self.game
            )

    def get_piece(self, rank: int, file: int) -> bool:
        """Get the piece on a square."""
        for move in self.hypothetical_moves or ():
            if move[1:3] == (rank, file):
                if len(move) > 3:
                    # Includes a promotion.
                    promotion = move[3]
                else:
                    promotion = None
                piece = move[0]
                p_type = promotion or piece.piece_type
                return MockPiece(piece, rank, file, p_type)
        return models.Piece.get_or_none(
            models.Piece.file == file, models.Piece.rank == rank,
            models.Piece.game == self.game
        )

    def path_is_empty(
            self, piece: models.Piece, rank: int, file: int) -> bool:
        """Check that all squares in a path are empty.

        The last square may be occupied by an enemy piece.
        """
        file_delta = file - piece.file
        rank_delta = rank - piece.rank
        steps = max(abs(file_delta), abs(rank_delta))
        file_step = file_delta // steps
        rank_step = rank_delta // steps

        # Intentionally not including the final step.
        for step in range(1, steps):
            this_file = piece.file + step * file_step
            this_rank = piece.rank + step * rank_step
            if self.get_piece(this_rank, this_file):
                return False

        victim = self.get_piece(rank, file)
        return victim.side != piece.side

    def on_board(self, rank: int, file: int) -> bool:
        """Check if valid square i.e. rank and file on board."""
        return 7 >= rank >= 0 and 7 >= file >= 0

    def get_moves_in_direction(
            self, piece: models.Piece, rank_direction: int,
            file_direction: int) -> typing.Iterator[int, int]:
        """Get all moves for a unit in a direction."""
        rank, file = piece.rank, piece.file
        while True:
            rank += rank_direction
            file += file_direction
            if not self.on_board(rank, file):
                break
            target = self.get_piece(rank, file)
            if (not target) or (target.side != piece.side):
                yield rank, file
            if target:
                break

    def hypothetical_check(
            self, side: enums.Side,
            *moves: tuple[
                tuple[models.Piece, int, int, enums.PieceType], ...
            ]) -> bool:
        """Check if a series of moves would put a side in check."""
        if self.hypothetical_moves is not None:    # pragma: no cover
            raise RuntimeError('Checkmate detection recursion detected.')
        self.hypothetical_moves = moves    # self.get_piece will observe this
        king = models.Piece.get(
            models.Piece.side == side,
            models.Piece.piece_type == enums.PieceType.KING,
            models.Piece.game == self.game
        )
        enemies = models.Piece.select().where(
            models.Piece.side == ~side,
            models.Piece.game == self.game
        )
        piece_changes = {}
        for move in moves:
            if len(move) == 3:
                # Add promotion.
                move = [*move, None]
            piece_changes[move[0].id] = (
                move[1], move[2], move[3] or move[0].piece_type
            )
        if king.id in piece_changes:
            king = MockPiece(king, *piece_changes[king.id])
        for enemy in enemies:
            if enemy.id in piece_changes:
                enemy = MockPiece(enemy, *piece_changes[enemy.id])
            check = self.validate_move(
                enemy.rank, enemy.file, king.rank, king.file,
                check_allowed=True, hypothetical_opponent_turn=True
            )
            if check:
                self.hypothetical_moves = None
                return True
        self.hypothetical_moves = None
        return False

    def validate_pawn_move(
            self, pawn: models.Piece, rank: int, file: int,
            promotion: enums.PieceType = None,
            validate_promotion: bool = True) -> bool:
        """Validate a pawn's move."""
        absolute_file_delta = abs(file - pawn.file)
        relative_rank_delta = pawn.side.forwards * (rank - pawn.rank)
        if relative_rank_delta == 0:
            return False
        elif relative_rank_delta == 1:
            if validate_promotion:
                if rank == (7 if pawn.side == enums.Side.HOST else 0):
                    if not promotion:
                        return False
                    if promotion in (
                            enums.PieceType.PAWN, enums.PieceType.KING):
                        return False
                else:
                    if promotion:
                        return False
            if absolute_file_delta == 0:
                return not self.get_piece(rank, file)
            elif absolute_file_delta == 1:
                victim = self.get_piece(rank, file)
                en_passant_pawn = self.get_piece(pawn.rank, file)
                en_passant_valid = (
                    en_passant_pawn and en_passant_pawn.side != pawn.side
                    and en_passant_pawn.first_move_last_turn
                    and pawn.rank == (
                        4 if pawn.side == enums.Side.HOST else 3
                    )
                )
                return (
                    victim.side != pawn.side if victim else en_passant_valid
                )
            else:
                return False
        elif relative_rank_delta == 2:
            if absolute_file_delta:
                return False
            if pawn.has_moved:
                return False
            return not bool(
                self.get_piece(rank, file)
                or self.get_piece(rank - pawn.side.forwards, file)
            )
        else:
            return False

    def get_pawn_moves(self, pawn: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a pawn."""
        options = ((1, 0), (2, 0), (1, -1), (1, 1))
        promotion_pieces = (
            enums.PieceType.ROOK, enums.PieceType.KNIGHT,
            enums.PieceType.BISHOP, enums.PieceType.QUEEN
        )
        promotion_rank = 7 if pawn.side == enums.Side.HOST else 0
        for absolute_rank_delta, file_delta in options:
            rank = pawn.rank + absolute_rank_delta * pawn.side.forwards
            file = pawn.file + file_delta
            valid = self.validate_pawn_move(
                pawn, rank, file, validate_promotion=False
            )
            if self.on_board(rank, file) and valid:
                if rank == promotion_rank:
                    for piece in promotion_pieces:
                        yield rank, file, piece
                else:
                    yield rank, file, piece

    def validate_rook_move(
            self, rook: models.Piece, rank: int, file: int,
            promotion: enums.PieceType = None) -> bool:
        """Validate a rook's move."""
        if promotion:
            return False
        file_delta = file - rook.file
        rank_delta = rank - rook.file
        if file_delta and rank_delta:
            return False
        return self.path_is_empty(rook, rank, file)

    def get_rook_moves(self, rook: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a rook."""
        for direction in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            for move in self.get_moves_in_direction(rook, *direction):
                yield move

    def validate_knight_move(
            self, knight: models.Piece, rank: int, file: int,
            promotion: enums.PieceType = None) -> bool:
        """Validate a knight's move."""
        if promotion:
            return False
        absolute_file_delta = abs(file - knight.file)
        absolute_rank_delta = abs(rank - knight.rank)
        if (absolute_file_delta, absolute_rank_delta) not in ((1, 2), (2, 1)):
            return False
        victim = self.get_piece(rank, file)
        return (not victim) or (victim.side != knight.side)

    def get_knight_moves(
            self, knight: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a knight."""
        for rank_absolute, file_absolute in ((1, 2), (2, 1)):
            for rank_direction in (-1, 1):
                for file_direction in (-1, 1):
                    rank = knight.rank + rank_absolute * rank_direction
                    file = knight.file + file_absolute * file_direction
                    victim = self.get_piece(rank, file)
                    if (not victim) or (victim.side != knight.side):
                        yield rank, file

    def validate_bishop_move(
            self, bishop: models.Piece, rank: int, file: int,
            promotion: enums.PieceType = None) -> bool:
        """Validate a bishop's move."""
        if promotion:
            return False
        absolute_file_delta = abs(file - bishop.file)
        absolute_rank_delta = abs(rank - bishop.rank)
        if absolute_file_delta != absolute_rank_delta:
            return False
        return self.path_is_empty(bishop, rank, file)

    def get_bishop_moves(
            self, bishop: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a bishop."""
        for direction in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            for move in self.get_moves_in_direction(bishop, *direction):
                yield move

    def validate_queen_move(
            self, queen: models.Piece, rank: int, file: int,
            promotion: enums.PieceType = None) -> bool:
        """Validate a queen's move."""
        if promotion:
            return False
        absolute_file_delta = abs(file - queen.file)
        absolute_rank_delta = abs(rank - queen.rank)
        bishops_move = absolute_file_delta == absolute_rank_delta
        rooks_move = bool(absolute_file_delta) ^ bool(absolute_rank_delta)
        if not (bishops_move or rooks_move):
            return False
        return self.path_is_empty(queen, rank, file)

    def get_queen_moves(
            self, queen: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a queen."""
        for file_direction in (-1, 0, 1):
            for rank_direction in (-1, 0, 1):
                direction = (rank_direction, file_direction)
                if direction == (0, 0):
                    continue
                for move in self.get_moves_in_direction(queen, *direction):
                    yield move

    def validate_king_move(
            self, king: models.Piece, rank: int, file: int,
            promotion: enums.PieceType = None) -> bool:
        """Validate a king's move."""
        if promotion:
            return False
        absolute_file_delta = abs(file - king.file)
        absolute_rank_delta = abs(rank - king.rank)
        # Check for castling attempt.
        if ((not absolute_rank_delta)
                and not king.has_moved and absolute_file_delta > 1):
            if file == 2:
                rook_start = 0
                rook_end = 3
                empty_files = (1, 2, 3)
            elif file == 6:
                rook_start = 7
                rook_end = 5
                empty_files = (5, 6)
            else:
                return False
            rook = self.get_piece(rank, rook_start)
            if (not rook) or rook.has_moved:
                return False
            for empty_file in empty_files:
                if self.get_piece(rank, empty_file):
                    return False
            if self.hypothetical_check(king.side):
                return False
            if self.hypothetical_check(king.side, (king, rank, rook_end)):
                return False
            return True
        if (absolute_file_delta > 1) or (absolute_rank_delta > 1):
            return False
        victim = self.get_piece(rank, file)
        return (not victim) or (victim.side != king.side)

    def get_king_moves(self, king: models.Piece) -> typing.Iterator[int, int]:
        """Get all possible moves for a king."""
        for file_direction in (-1, 0, 1):
            for rank_direction in (-1, 0, 1):
                direction = (rank_direction, file_direction)
                if direction == (0, 0):
                    continue
                rank = king.rank + rank_direction
                file = king.file + file_direction
                if not self.on_board(rank, file):
                    continue
                victim = self.get_piece(rank, file)
                if (not victim) or (victim.side != king.side):
                    yield rank, file
        if not king.has_moved:
            for file_direction in (-2, 2):
                file = king.file + file_direction
                if self.validate_king_move(king, king.rank, file):
                    yield king.rank, file

    def validate_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int, promotion: enums.PieceType = None,
            check_allowed: bool = False,
            hypothetical_opponent_turn: bool = False) -> bool:
        """Validate a move, without first converting the parameters."""
        if start_file == end_file and start_rank == end_rank:
            return False
        piece = self.get_piece(start_rank, start_file)
        if not piece:
            return False
        if not self.on_board(end_rank, end_file):
            return False
        if (
                (piece.side != self.game.current_turn)
                and (not hypothetical_opponent_turn)):
            return False
        validators = {
            enums.PieceType.PAWN: self.validate_pawn_move,
            enums.PieceType.ROOK: self.validate_rook_move,
            enums.PieceType.KNIGHT: self.validate_knight_move,
            enums.PieceType.BISHOP: self.validate_bishop_move,
            enums.PieceType.QUEEN: self.validate_queen_move,
            enums.PieceType.KING: self.validate_king_move
        }
        if not validators[piece.piece_type](
                piece, end_rank, end_file, promotion):
            return False
        return check_allowed or not self.hypothetical_check(
            piece.side, (piece, end_rank, end_file)
        )

    @utils.converters.wrap
    def make_move(
            self, start_rank: int, start_file: int, end_rank: int,
            end_file: int, promotion: enums.PieceType = None) -> bool:
        """Validate and apply move."""
        valid = self.validate_move(
            start_rank, start_file, end_rank, end_file, promotion
        )
        if not valid:
            return False
        piece = self.get_piece(start_rank, start_file)
        piece.rank = end_rank
        piece.file = end_file
        piece.first_move_last_turn = not piece.has_moved
        piece.has_moved = True
        if promotion:
            piece.piece_type = promotion
        piece.save()
        target = self.get_piece(end_rank, end_file)
        if target:
            target.delete_instance()
        if target or piece.piece_type == enums.PieceType.PAWN:
            self.game.last_kill_or_pawn_move = int(self.game.turn_number)
            self.game.save()
        return True

    def possible_moves(self, side: enums.Side) -> typing.Iterator[
            tuple[models.Piece, int, int]]:
        """Get all possible moves for a side."""
        pieces = models.Piece.select().where(
            models.Piece.side == side,
            models.Piece.game == self.game
        )
        move_generators = {
            enums.PieceType.PAWN: self.get_pawn_moves,
            enums.PieceType.ROOK: self.get_rook_moves,
            enums.PieceType.KNIGHT: self.get_knight_moves,
            enums.PieceType.BISHOP: self.get_bishop_moves,
            enums.PieceType.QUEEN: self.get_queen_moves,
            enums.PieceType.KING: self.get_king_moves
        }
        for piece in pieces:
            for move in move_generators[piece.piece_type](piece):
                move = (piece.rank, piece.file, *move)
                if len(move) == 4:
                    move = (*move, None)    # Add null promotion if not given.
                if not self.hypothetical_check(side, move):
                    yield {
                        'start_rank': move[0],
                        'start_file': move[1],
                        'end_rank': move[2],
                        'end_file': move[3],
                        'promotion': move[4]
                    }

    def game_is_over(self) -> enums.Conclusion:
        """Check if the game has been won or tied.

        If the return value is checkmate, the player whos turn it currently
        is is in checkmate. This method must be called after the GameState
        for the current turn has been created. Note that a return of
        THREEFOLD_REPETITION or FIFTY_MOVE_RULE should not immediately end the
        game - rather, at least one player must claim the draw.
        """
        current_state = models.GameState.get(
            models.GameState.game == self.game,
            models.GameState.turn_number == int(self.game.turn_number)
        )
        identical_states = models.GameState.select().where(
            models.GameState.game == self.game,
            models.GameState.arrangement == current_state.arrangement
        )
        if len(list(identical_states)) >= 3:
            return enums.Conclusion.THREEFOLD_REPETITION
        if self.game.turn_number >= self.game.last_kill_or_pawn_move + 50:
            return enums.Conclusion.FIFTY_MOVE_RULE
        moves_available = list(self.possible_moves(self.game.current_turn))
        if moves_available:
            return enums.Conclusion.GAME_NOT_COMPLETE
        if self.hypothetical_check(self.game.current_turn):
            return enums.Conclusion.CHECKMATE
        return enums.Conclusion.STALEMATE

    def freeze_game(self) -> str:
        """Store a snapshot of a game as a string."""
        pieces = models.Piece.select().where(
            models.Piece.game == self.game
        ).order_by(
            models.Piece.rank, models.Piece.file
        )
        arrangement = ''
        castling_options = []
        for side in (self.game.current_turn, ~self.game.current_turn):
            king = models.Piece.get(
                models.Piece.game == self.game,
                models.Piece.side == side,
                models.Piece.piece_type == enums.PieceType.KING
            )
            if not king.has_moved:
                for file_direction in (-2, 2):
                    file = king.file + file_direction
                    if self.validate_king_move(king, king.rank, file):
                        castling_options.append((king.id, file_direction))
        for piece in pieces:
            if piece.piece_type == enums.PieceType.KNIGHT:
                abbrev = 'n'
            else:
                abbrev = piece.piece_type.name[0]
            if piece.side == enums.Side.HOST:
                abbrev = abbrev.upper()
            arrangement += (
                abbrev + str(models.Piece.rank) + str(models.Piece.file)
            )
            if piece.piece_type == enums.PieceType.PAWN:
                if piece.first_move_last_turn:
                    arrangement += 'X'
            elif piece.piece_type == enums.PieceType.KING:
                if (piece.id, -2) in castling_options:
                    arrangement += 'X'
                if (piece.id, 2) in castling_options:
                    arrangement += 'Y'
        return arrangement
