#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render GUIDE_TESTEUR.md from atp_scenarios.py.

The guide gives a tester the commands of every toolchain scenario as plain text
blocks: a multi-line spreadsheet cell gains quotes when it is copied, a code
block does not. It is generated so that it cannot drift from the workbook.

    python3 scripts/build_guide.py [output.md]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atp_scenarios import SCENARIOS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SECTIONS = [
    ("ENV", "ENV — environnement"),
    ("STACK", "STACK — analyseur de pile (coretrace-stack-analyzer)"),
    ("CONC", "CONC — analyseur de concurrence (coretrace-concurrency-analyzer)"),
    ("RUN", "RUN — analyseur runtime (coretrace-runtime-analyzer)"),
    ("CORE", "CORE — orchestrateur (coretrace)"),
]

INTRO = """\
# Parcours testeur — ATP CoreTrace (partie toolchain)

Ce guide accompagne la **partie 1** du plan (la toolchain). Le point d'entrée du
plan est `README.md` : lisez-le d'abord, il indique quel document ouvrir et quand.

Ce guide reprend, dans l'ordre, les commandes des {count} scénarios toolchain du
classeur ATP. Les commandes et les résultats attendus sont ceux de la colonne
*Steps* et *Expected results* du classeur, en anglais ; copiez les commandes
depuis ce fichier plutôt que depuis une cellule Excel.

La **partie 2** (l'application de bureau, scénarios `GUI-F…`) a son propre
environnement et sa propre notice : voir la section 5 de `README.md`.

## Avant de commencer

1. Lisez `README.md` (prérequis, que faire si le build échoue).
2. Démarrez Docker et ouvrez un terminal.
3. Déroulez `ENV-02` ci-dessous : il récupère le dépôt (si ce n'est pas déjà fait),
   construit l'image et ouvre le conteneur.

À partir de là, **toutes les commandes se tapent dans le conteneur**. Chaque
bloc commence par `cd /atp` pour repartir du bon dossier. Si vous quittez le
conteneur (`exit`), relancez simplement `./atp.sh linux`.

Pour chaque scénario, remplissez la colonne **Feedback** du classeur avec `OK`,
`KO` ou `Not run`, puis ce que vous avez vu. `OK` seulement si **tout** ce qui
est décrit dans « Attendu » est observé.
"""

OUTRO = """\
## Signaler une anomalie

Une issue GitHub par anomalie, dans le dépôt indiqué par la clé du scénario
(STACK, CONC, RUN : le dépôt de l'analyseur ; CORE et ENV : `coretrace`), avec
la clé dans le titre, par exemple `[STACK-05] index off by one not reported`.
Joignez la commande exacte, la sortie complète et le résultat de :

```bash
./atp.sh versions       # sur votre machine ; ou : cat /atp/VERSIONS dans le conteneur
```
"""


def block(sc: dict) -> str:
    steps = list(sc["steps"])
    if not sc["id"].startswith("ENV"):
        steps.insert(0, "cd /atp")
    eip = f" ({sc['eip']})" if sc.get("eip") and f"({sc['eip']})" not in sc["name"] else ""
    return (f"### {sc['id']} — {sc['name']}{eip}\n\n"
            "```bash\n" + "\n".join(steps) + "\n```\n\n"
            f"**Attendu :** {sc['expected']}\n")


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "GUIDE_TESTEUR.md"
    parts = [INTRO.format(count=len(SCENARIOS))]
    for prefix, title in SECTIONS:
        scenarios = [sc for sc in SCENARIOS if sc["id"].startswith(prefix + "-")]
        if scenarios:
            parts.append(f"## {title}\n")
            parts.extend(block(sc) for sc in scenarios)
    parts.append(OUTRO)
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"{out}  ({len(SCENARIOS)} scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
