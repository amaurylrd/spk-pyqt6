from collections import defaultdict
from random import choice

from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from unidecode import unidecode

from games.bingo import BingoGrid
from games.motus import MotusGrid
from games.teams import MotusTeam
from glcore.application import Application, MediaPlayer

DICTIONARY: dict[int, set[str]] = defaultdict(
    set,
    {
        6: {"lutins", "pastis", "jungle", "dentel", "python", "souple", "buffet"},
        7: {"complet", "hauteur"},
        8: {"calibre", "pipeline", "remorquer"},
    },
)


class MotusEngine(Application):
    """The Motus game engine class."""

    MAX_ATTEMPTS = 6

    def __init__(self, n):
        self.i = 0  # current attempt
        self.j = 0  # current letter
        self.k = 0  # current team
        self.n = n  # number of teams
        self.is_playing = False

        super().__init__()

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)

        if not self.is_playing:
            self.setup_word()
            self.is_playing = True
            return

        if event.isAutoRepeat() and not event.key() == Qt.Key.Key_Backspace:
            return

        if event.text().isalpha():
            if self.j < len(self.secret_word):
                self.grid.motus[self.i][self.j].active = False
                self.grid.motus[self.i][self.j].text = unidecode(event.text()).upper()
                self.grid.motus[self.i][self.j].repaint()
                self.j += 1

                if self.j < len(self.secret_word):
                    self.grid.motus[self.i][self.j].active = True
                    self.grid.motus[self.i][self.j].repaint()

        elif event.key() == Qt.Key.Key_Backspace:
            if self.j > 0:
                if self.j != len(self.secret_word):
                    self.grid.motus[self.i][self.j].active = False
                    self.grid.motus[self.i][self.j].repaint()

                self.j -= 1
                self.grid.motus[self.i][self.j].active = True
                self.grid.motus[self.i][self.j].text = self.secret_word[self.j] if self.grid.corrects[self.j] else "."
                self.grid.motus[self.i][self.j].repaint()

        elif event.key() == Qt.Key.Key_Return:
            if self.j < len(self.secret_word):
                self.grid.motus[self.i][self.j].active = False
                self.grid.motus[self.i][self.j].repaint()

            guess = "".join(label.text if i < self.j else " " for i, label in enumerate(self.grid.motus[self.i]))

            self.grid.update_line(self.i, self.j, self.secret_word, guess)

            match_found = self.j == len(self.secret_word) and guess == self.secret_word

            if match_found or self.i == self.MAX_ATTEMPTS - 1:
                if match_found:
                    MediaPlayer.play("victory")
                    self.grid.shine(self.i)
                    QThread.msleep(100)
                    self.teams[self.k].score += (self.MAX_ATTEMPTS - self.i) * 10
                    self.teams[self.k].draw_balls()
                else:
                    MediaPlayer.play("loose")
                    self.grid.update_line(self.i, self.j, self.secret_word)

                QThread.msleep(3000)

                self.teams[self.k].active = False
                self.teams[self.k].repaint()
                self.k = (self.k + 1) % self.n
                self.setup_word()
            else:
                self.i += 1
                self.j = 0
                self.grid.setup_line(self.i, self.secret_word)

    def init(self, container: QWidget):
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        container.setLayout(main_layout)

        left_bar = QVBoxLayout()
        left_bar.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.bingo_grids = QStackedWidget(container)
        self.bingo_grids.setFixedHeight(int(container.width() * 0.25))
        left_bar.addWidget(self.bingo_grids)

        teams_layout = QVBoxLayout()
        teams_layout.setContentsMargins(0, 0, 10, 0)
        teams_layout.setSpacing(10)
        self.teams = []
        for i in range(self.n):
            self.bingo_grids.addWidget(BingoGrid(i, container))
            self.teams.append(MotusTeam(i, self.bingo_grids))
            teams_layout.addWidget(self.teams[i])
        left_bar.addLayout(teams_layout)
        main_layout.addLayout(left_bar)

        self.grid = MotusGrid(container)
        self.grid.setFixedHeight(container.height())
        self.grid.setFixedWidth(int(container.width() * 0.75))
        main_layout.addWidget(self.grid)

    def setup_word(self):
        self.teams[self.k].active = True
        self.teams[self.k].repaint()

        self.i, self.j = 0, 0
        self.secret_word = self.get_secret_word()
        self.grid.setup(self.MAX_ATTEMPTS, len(self.secret_word))
        self.grid.setup_line(0, self.secret_word)
        self.bingo_grids.setCurrentIndex(self.k)

        if not self.bingo_grids.currentWidget().remaining_balls:
            self.bingo_grids.currentWidget().init_grid_animation()

    def get_secret_word(self) -> str:
        keys = list(k for k, v in DICTIONARY.items() if len(v) >= self.n)
        key = choice(keys)

        return unidecode(DICTIONARY[key].pop()).upper()
