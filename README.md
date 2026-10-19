# Forge Oracle

Predict the next Forge of Potential results in Valheim from your character save, before you spend an idol.

Forge of Potential rolls are not random at the moment you click. Each item and target level has a seed stored in your `.fch` character file. Each attempt turns that seed into one roll, then saves a new seed. Reloading cannot change an outcome, so upcoming results can be read ahead of time.

Unofficial fan tool. Not affiliated with or endorsed by Iron Gate AB. Single-player only. Read-only: it never modifies your save.

## Use it in the browser

Open `index.html` (or the hosted page, if you publish one).

1. Drop your character file onto the page. Everything runs locally in your browser; the file is never uploaded. No save file, for example on console? Skip this step and type your character name in step 2.
2. Pick one of the slots found in your save, or type an item's internal name (for example `Hammer`) and its current level.
3. Read the next ten upgrade steps for that item: row 1 is current level to +1, row 2 is +1 to +2, and so on, each with its predicted result and roll. The rows after the first assume every earlier step succeeded, since a failure breaks the item.

### Reading the results

- **Results to show.** The default shows the next result for each step. Choose "Next two results" or "Next three results" to see the 2nd and 3rd side by side. A step's results belong to the item type, not to one copy, so a second copy of the same item uses the next unused result on each step the first copy reached, and the 1st result on steps it did not reach.
- **Used so far.** With a save loaded, a step that has already been attempted shows its attempt number and the results already used, for example "Attempt 2 on this step. Already used: Fail". The page works this out by counting forward from the character name until it reaches the seed stored in the save. If the name is wrong it says so and leaves the history out.
- **Earlier attempts (no save needed).** Without a save, for example on console, every step starts from the character name. Each step has an "Earlier attempts on this step" box. Enter how many attempts the character has already made there and the page skips that many results and shows what they would have been, so you can compare with what you remember. The name has to match exactly, including capitals. This has been tested on PC saves only.

The page also has an "Item names and IDs" list with search. Tap an item to fill in its internal name, and an experimental "Find a starting name" section (see below).

The character name is read from the save automatically. It only matters for an item and level that has no stored seed yet, where the starting seed comes from the name.

On Windows, character files live in:

```
%USERPROFILE%\AppData\LocalLow\IronGate\Valheim\characters_local
```

The game writes seeds to the file only when it saves, so quit to the main menu after an attempt before loading the file.

## Use it from the command line

`forge_predict.py` needs only Python 3. It prints the same list as the page.

```
python forge_predict.py --item Hammer --level 3 --fch Thor.fch
```

| Option | Meaning |
| --- | --- |
| `--item` | The item's internal name, not its display name. Look names up in the [Valheim item ID list](https://www.valheim.tools/item-ids) |
| `--level` | The item's current level. Row 1 is current to +1, row 2 is +1 to +2, and so on |
| `--fch` | Your character file. Stored seeds are used and the character name is read from it |
| `--name` | Character name. Only needed without `--fch`, or if the name could not be read |
| `--count` | How many upgrade steps to list (default 10) |
| `--search` | Search for character names with a long success streak for `--item`, starting after `--level` (see below) |
| `--max-len` | With `--search`, the longest name to try (default 4, and 5 is slow) |
| `--names` | With `--search`, a text file of candidate names, one per line, instead of the generated names |
| `--top` | With `--search`, how many names to list (default 10) |

`fch_tail.py` prints the save version, checksum status and the raw seed tables from a `.fch` file. It is a debugging aid.

## How it works

These details were read from the game's own code and then checked against real saves.

1. The key is `hash(item name) + target level`, using Valheim's string hash.
2. The seed is the one stored for that key in the save. If there is none, it is `hash(character name) + key`.
3. Unity's random generator is seeded with it and one value between 0 and 1 is drawn. That is the roll.
4. A second draw, taken modulo 99999999, is stored as the new seed for that key. This happens on every attempt, before the result is judged.
5. A roll of 0.65 or less succeeds. A higher roll fails, and a failed upgrade destroys the item. Every idol tier has the same odds.

Things that follow from this:

- Reloading a save does not reroll an attempt.
- Two items with the same internal name at the same target level share one sequence.
- A different item or a different level is a separate sequence.
- After a success, the next upgrade of that item uses the next level's slot, which has a fresh sequence.
- The sequences belong to the character, not the item. See the next section.

### Trading items between characters (inferred, not yet tested in game)

The seed is stored in the character that does the upgrade, not on the item. If a different character upgrades the same item, the game uses that character's own sequence for that item and level. A character that has never attempted it starts from `hash(its name) + key`, so its first roll is fixed by its name.

If this holds, passing an item to another character changes the predicted result, and you can check it first: drop that character's `.fch` onto the page and it shows that character's next ten attempts. Each character's sequence advances only on its own attempts. A failure still destroys the item.

One limit, confirmed in play: a character cannot upgrade an item type, at the workbench or the Forge, until that character has crafted a copy of it. An item that was given to a character cannot be upgraded until then. So the other character needs to have crafted the item first. Picking up the materials is not enough.

This follows from the decompiled code but has not been confirmed with a real trade. If you test it, please open an issue with the result.

### Finding a starting name (experimental)

For a brand-new character, the first roll for an item and level comes from `hash(character name) + key`, so the name decides how a fresh character's first upgrades go. The tool can search for names whose first rolls succeed several levels in a row:

```
python forge_predict.py --item Hammer --level 1 --search
```

The page has the same search under "Find a starting name". It tries every capitalized name of 3 to 4 letters (about 475,000, a couple of seconds). Tap a result on the page to see that name's next ten upgrades.

- A streak of n in a row turns up in about 0.65^n of names, so 5 in a row is roughly 1 name in 9 and 8 in a row is roughly 1 in 30. Longer streaks need more names tried.
- The result is for one item. Another item has a different key, so it needs its own search.
- It only helps a character that has never tried that item at those levels. After an attempt, the saved seed takes over from the name.
- The new character has to craft one of that item before it can upgrade it (see the trading section above), so it only suits items the character can make. Crafting does not touch the seeds: in the game code only the save, the load and the upgrade roll use the seed table.
- It only looks at the first roll per level. It does not model failing on purpose to advance a queue, which [ValheimSaveParser](https://github.com/Melichor/ValheimSaveParser) covers.
- This has not been tested in game, and it has not been checked which names the game accepts. If you try one, please open an issue with the result.

### Save format (version 47, game 1.0.20)

```
[u32 payloadLength][payload][u32 64][SHA-512 of payload]
```

Near the end of the payload is the build-menu blob: a list of known build pieces, then one u32, then a list of known crafting stations (name plus a u32 each; empty on a character that has not used any, which is why the first saves tested did not show it). After it come two lists. The second is the Forge seed list: a count followed by `(u32 key, u32 seed)` pairs. The first is a separate list of drop counters, which the Forge does not use.

## What is verified

- The seed-to-roll math matched 14 consecutive real hammer attempts (26 real attempts in total with the chest test below), including every following seed.
- Those attempts rolled 0.5535 (success) and 0.6602 (fail), which fits a cutoff of 0.65.
- [ValheimSaveParser](https://github.com/Melichor/ValheimSaveParser) reads the same mechanics independently, including the 0.65 chance and the starting seed from the character name.
- Three copies of the same chest (`ArmorDeepNorthMediumChest`, level 6) were upgraded one after another. They broke at steps 4, 6 and 2, exactly as the shared results predicted (12 attempts).
- Entering the earlier attempts by hand, with no save loaded, gives the same results as loading the save.
- The key and seed layout match the game's decompiled `Player.GetItemUpgradeChance`.
- The character name detection returned the right name on every save tested.

## Known limits

- The 0.65 success chance and the "every failure breaks the item" rule come from the game data as extracted by [ValheimSaveParser](https://github.com/Melichor/ValheimSaveParser). Our own attempts only tested the wood idol, but that project's extraction found the same odds on every upgrader item.
- The built-in item list (271 weapons, armour, shields and tools that can be upgraded) is based on [valheim.tools](https://www.valheim.tools/item-ids), narrowed to the items [ValheimSaveParser](https://github.com/Melichor/ValheimSaveParser) lists as upgradable, in October 2026. It covers names that exist in game version 1.0.20 at that time and may miss newer items. A wrong name gives a plausible but wrong prediction.
- Name detection looks for the name stored next to your character ID. A character with no crafted items, or with many items crafted by someone else, may need the name entered by hand.
- The "earlier attempts" boxes depend on you counting correctly. A wrong count shifts every result for that step.
- Without a save, results are only right for steps the character has not attempted beyond the number you enter.
- Seeds that do not match a built-in item (levels 1 to 20) are counted as "outside the built-in list", and you can type their internal name to look at them.
- The name search and the character-trading idea follow from the game code but have not been tested in game.
- The page finds the seed table by matching the layout at the end of the file, not by reading the whole file. A character with an unusual layout, for example from a mod, may still be rejected; the page then names the save version. The crafting-station list was missed at first and fixed after a user's save showed it (tested on 36 version-47 saves).
- A game patch can change the math or the save format.

If a prediction ever misses, open an issue with the save from before the attempt, the save from after it, and what happened.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | The browser tool, a single self-contained file |
| `forge_predict.py` | Command line predictor |
| `fch_tail.py` | Save inspector |

## License

Add a license before publishing, for example MIT.
