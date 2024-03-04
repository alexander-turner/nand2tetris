import classes
import time

if __name__ == "__main__":
    name: str = input("What's your name? ")

    goose_preference: str = input("Do you like geese? [Y/n] ")
    power_up: bool = goose_preference == "Y"
    hitpoints: int = 10 + 500 * power_up

    main_character = classes.Player(
        hitpoints=hitpoints, equipped_items=[], dropped_items=[], name=name
    )

    print("The goblin king roars at you. STOP GOOFING OFF! PAY ATTENTION TO ME!")
    print(
        "\nApparently he didn't take too kindly to you thinking about geese just now."
    )
    input("[Press Enter to continue...]")

    print("\nBut you can't help yourself. Geese are great.")

    time.sleep(2)
    print("...\n\n")

    time.sleep(2)
    print("\n\nHonk!\n")  # TODO add a goose ASCII art here

    goblin_king = classes.Goblin(
        hitpoints=10, name="Goblin", dropped_items=["The Philosopher's Stone"]
    )

    print(
        "The goblin king bellows and charges. You look down and realize you're totally naked. Oops."
    )

    main_character.combat(goblin_king)
