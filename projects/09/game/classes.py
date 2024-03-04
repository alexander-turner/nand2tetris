from typing import Literal, List, Union
from dataclasses import dataclass
import random
import time


@dataclass(frozen=True)
class Item:
    value: int  # GP value
    rarity: Literal["Common", "Uncommon", "Rare", "Legendary"]


class Weapon(Item):
    attack_bonus: int
    damage_bonus: int


class Armor(Item):
    defense_bonus: int


class Gemstone(Item):
    value = 100
    rarity = "Rare"


# PCs and NPCs
@dataclass
class Character:
    hitpoints: int
    name: str  # f"{name} attacks!"

    equipped_items: List[Union[Weapon, Armor]] = tuple()
    dropped_items: List[Item] = tuple()
    last_words: str = "Honk!"  # Printed after death

    def __post_init__(self):
        self.current_hitpoints = self.hitpoints


class Player(Character):
    hitpoints = 20
    name = "Player"

    def combat(self, enemy: Character):
        def _combat_continues() -> bool:
            return self.current_hitpoints > 0 and enemy.current_hitpoints > 0

        while _combat_continues():
            # Player's turn
            print(f"You attack the {enemy.name}!")
            damage: int = random.randint(0, 5)
            print(
                f"You do {damage} damage. The {enemy.name} has {enemy.current_hitpoints} HP left.\n"
            )

            time.sleep(1)
            enemy.current_hitpoints -= damage
            # Enemy's turn
            damage: int = random.randint(0, 5)
            print(f"{enemy.name} attacks you!")
            print(
                f"The {enemy.name} does {damage} damage. You have {self.current_hitpoints} HP left.\n"
            )
            self.current_hitpoints -= damage
            time.sleep(1)

        if self.current_hitpoints <= 0:
            print(self.last_words)
        else:
            print(
                f"The {enemy.name} is defeated! In their final words, they croak: {enemy.last_words}"
            )
        print(f"You looted: {enemy.dropped_items}")


class Goblin(Character):
    hitpoints = 10
    name = "Goblin"
    last_words = "Glorkel will make you pay for this!!"
