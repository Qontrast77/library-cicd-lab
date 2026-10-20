"""Шаг 8: консольное приложение для изменения набора данных data/books.csv.

Команды:
  stats                         статистика набора (строки, жанры, md5)
  list   [--genre G] [--search S] [--limit N]
  show   ID                     показать запись полностью
  add    --title T --genre G --summary S
  edit   ID [--title T] [--genre G] [--summary S]
  delete ID [ID ...]
  import FILE.csv               добавить записи из CSV (колонки title, genre, summary)
  remove-genre G                удалить все книги жанра
  sample --fraction F           оставить случайную долю записей (демонстрация ухудшения)
  noise  --fraction F           перемешать метки у доли записей (демонстрация ухудшения)
  validate                      проверка набора перед обучением (используется в Jenkins)

Ключи для изменяющих команд:
  --commit   сделать git commit изменённого data/books.csv
  --push     commit + git push (запускает переобучение в Jenkins)

Примеры:
  python ml/data_tool.py stats
  python ml/data_tool.py add --title "Dune" --genre science --summary "..." --push
  python ml/data_tool.py noise --fraction 0.4 --push
"""
import argparse
import subprocess
import sys

import pandas as pd

from common import COLUMNS, ROOT, TRAIN_FILE, file_md5, fix_console, load_dataset, save_dataset

MIN_ROWS_PER_GENRE = 10
MIN_SUMMARY_LEN = 20


def known_genres(df):
    return sorted(df["genre"].unique())


def next_id(df):
    return int(df["id"].max()) + 1 if len(df) else 1


def find(df, rid):
    idx = df.index[df["id"] == rid]
    if not len(idx):
        raise SystemExit(f"Запись с id={rid} не найдена")
    return idx[0]


def check_genre(df, genre, allow_new):
    if genre not in known_genres(df) and not allow_new:
        raise SystemExit(f"Неизвестный жанр '{genre}'. Известные: {', '.join(known_genres(df))}. "
                         f"Чтобы добавить новый жанр, укажите --new-genre")


# ---------------------------------------------------------------- команды
def cmd_stats(df, a):
    print(f"Файл: {TRAIN_FILE.relative_to(ROOT)}")
    print(f"Записей: {len(df)}   жанров: {df['genre'].nunique()}   md5: {file_md5(TRAIN_FILE)}")
    print(f"Средняя длина аннотации: {df['summary'].str.len().mean():.0f} символов\n")
    print(df["genre"].value_counts().rename("книг").to_string())


def cmd_list(df, a):
    v = df
    if a.genre:
        v = v[v["genre"] == a.genre]
    if a.search:
        v = v[v["title"].str.contains(a.search, case=False, na=False)]
    for _, r in v.head(a.limit).iterrows():
        print(f"{r['id']:>5}  {r['genre']:<11} {r['title'][:60]}")
    print(f"--- показано {min(a.limit, len(v))} из {len(v)}")


def cmd_show(df, a):
    r = df.loc[find(df, a.id)]
    print(f"id: {r['id']}\nНазвание: {r['title']}\nЖанр: {r['genre']}\nАннотация:\n{r['summary']}")


def cmd_add(df, a):
    check_genre(df, a.genre, a.new_genre)
    rid = next_id(df)
    df = pd.concat([df, pd.DataFrame([{"id": rid, "title": a.title, "genre": a.genre,
                                       "summary": a.summary}])], ignore_index=True)
    return df, f"добавлена книга id={rid} '{a.title}' ({a.genre})"


def cmd_edit(df, a):
    i = find(df, a.id)
    if a.genre:
        check_genre(df, a.genre, a.new_genre)
    for col in ("title", "genre", "summary"):
        if getattr(a, col):
            df.at[i, col] = getattr(a, col)
    return df, f"изменена книга id={a.id}"


def cmd_delete(df, a):
    for rid in a.ids:
        find(df, rid)
    df = df[~df["id"].isin(a.ids)]
    return df, f"удалены книги id={', '.join(map(str, a.ids))}"


def cmd_import(df, a):
    new = pd.read_csv(a.file, encoding="utf-8")
    missing = {"title", "genre", "summary"} - set(new.columns)
    if missing:
        raise SystemExit(f"В {a.file} нет колонок {sorted(missing)}")
    new = new[["title", "genre", "summary"]].dropna()
    new["genre"] = new["genre"].str.strip().str.lower()
    new.insert(0, "id", range(next_id(df), next_id(df) + len(new)))
    df = pd.concat([df, new], ignore_index=True)
    return df, f"импортировано {len(new)} книг из {a.file}"


def cmd_remove_genre(df, a):
    n = int((df["genre"] == a.genre).sum())
    if not n:
        raise SystemExit(f"Книг жанра '{a.genre}' нет")
    return df[df["genre"] != a.genre], f"удалён жанр '{a.genre}' ({n} книг)"


def cmd_sample(df, a):
    out = df.sample(frac=a.fraction, random_state=a.seed).sort_values("id")
    return out, f"оставлено {len(out)} из {len(df)} записей ({a.fraction:.0%})"


def cmd_noise(df, a):
    df = df.copy()
    idx = df.sample(frac=a.fraction, random_state=a.seed).index
    df.loc[idx, "genre"] = df.loc[idx, "genre"].sample(frac=1, random_state=a.seed + 1).values
    return df, f"перемешаны метки у {len(idx)} записей ({a.fraction:.0%})"


def cmd_validate(df, a):
    errors = []
    if df["id"].duplicated().any():
        errors.append(f"повторяющиеся id: {df.loc[df['id'].duplicated(), 'id'].tolist()[:10]}")
    for col in ("title", "genre", "summary"):
        n = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
        if n:
            errors.append(f"пустые значения в '{col}': {n}")
    short = int((df["summary"].astype(str).str.len() < MIN_SUMMARY_LEN).sum())
    if short:
        errors.append(f"аннотаций короче {MIN_SUMMARY_LEN} символов: {short}")
    counts = df["genre"].value_counts()
    small = counts[counts < MIN_ROWS_PER_GENRE]
    if len(small):
        errors.append(f"жанры с менее чем {MIN_ROWS_PER_GENRE} книгами: {small.to_dict()}")
    print(f"Записей: {len(df)}, жанров: {len(counts)}, md5: {file_md5(TRAIN_FILE)}")
    if errors:
        print("Набор данных НЕ прошёл проверку:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("Набор данных корректен.")


# ---------------------------------------------------------------- git
def git(*args):
    print("$ git " + " ".join(args))
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def commit(message, push):
    git("add", str(TRAIN_FILE.relative_to(ROOT)))
    git("commit", "-m", f"data: {message}")
    if push:
        git("push")


def main():
    fix_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def changing(name, func, help_):
        s = sub.add_parser(name, help=help_)
        s.add_argument("--commit", action="store_true", help="git commit изменений")
        s.add_argument("--push", action="store_true", help="git commit + push")
        s.set_defaults(func=func, changes=True)
        return s

    def reading(name, func, help_):
        s = sub.add_parser(name, help=help_)
        s.set_defaults(func=func, changes=False)
        return s

    reading("stats", cmd_stats, "статистика набора")
    s = reading("list", cmd_list, "список записей")
    s.add_argument("--genre")
    s.add_argument("--search")
    s.add_argument("--limit", type=int, default=20)
    s = reading("show", cmd_show, "показать запись")
    s.add_argument("id", type=int)
    reading("validate", cmd_validate, "проверка набора")

    s = changing("add", cmd_add, "добавить книгу")
    s.add_argument("--title", required=True)
    s.add_argument("--genre", required=True, type=str.lower)
    s.add_argument("--summary", required=True)
    s.add_argument("--new-genre", action="store_true", help="разрешить новый жанр")
    s = changing("edit", cmd_edit, "изменить книгу")
    s.add_argument("id", type=int)
    s.add_argument("--title")
    s.add_argument("--genre", type=str.lower)
    s.add_argument("--summary")
    s.add_argument("--new-genre", action="store_true")
    s = changing("delete", cmd_delete, "удалить книги")
    s.add_argument("ids", type=int, nargs="+")
    s = changing("import", cmd_import, "импорт из CSV")
    s.add_argument("file")
    s = changing("remove-genre", cmd_remove_genre, "удалить жанр целиком")
    s.add_argument("genre", type=str.lower)
    for name, func, h in (("sample", cmd_sample, "оставить долю записей"),
                          ("noise", cmd_noise, "перемешать метки у доли записей")):
        s = changing(name, func, h)
        s.add_argument("--fraction", type=float, required=True)
        s.add_argument("--seed", type=int, default=0)

    a = p.parse_args()
    if not TRAIN_FILE.exists():
        raise SystemExit(f"{TRAIN_FILE} не найден. Сначала выполните: python ml/prepare_data.py")
    df = load_dataset()

    if not a.changes:
        a.func(df, a)
        return

    before = file_md5(TRAIN_FILE)
    df, message = a.func(df, a)
    save_dataset(df[COLUMNS])
    print(f"Готово: {message}")
    print(f"Записей: {len(df)}; md5: {before} -> {file_md5(TRAIN_FILE)}")
    if a.commit or a.push:
        commit(message, a.push)
        if a.push:
            print("Изменения отправлены в GitHub - Jenkins запустит переобучение.")


if __name__ == "__main__":
    main()
