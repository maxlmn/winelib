"""Migration 0004: the wishlist's entries become a list flagged as the wishlist (any vintage: a cuvée entry; the note,
the link and an unusual size in the entry's note), and its table goes."""
from alembic import command
from sqlalchemy import create_engine, inspect, text

import migrate


def test_the_wishlist_moves_to_a_list(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'w.db'}")
    with engine.begin() as c:
        command.upgrade(migrate.config(c), "0003")
        c.execute(text("INSERT INTO producers (id, name) VALUES (1, 'Clos Rougeard')"))
        c.execute(text("INSERT INTO wines (id, producer_id, cuvee, vintage, type) VALUES (1, 1, 'Le Bourg', '2016', 'Red'), "
                       "(2, 1, 'Les Poyeux', '2018', 'Red')"))
        c.execute(text("INSERT INTO wishlist (wine_id, any_vintage, bottle_size, note, url, added) VALUES "
                       "(1, 0, '75cl', 'For 2030', 'https://shop.example/bourg', '2026-10-01'), "
                       "(2, 1, '150cl', NULL, NULL, '2026-10-02')"))
    migrate.upgrade(engine)
    with engine.connect() as c:
        assert "wishlist" not in inspect(c).get_table_names()
        lst = c.execute(text("SELECT id, name, is_wishlist FROM lists")).fetchall()
        assert [(r[1], bool(r[2])) for r in lst] == [("Wishlist", True)]
        items = c.execute(text("SELECT kind, wine_id, producer_id, note FROM list_items ORDER BY position")).fetchall()
        assert [tuple(r) for r in items] == [("wine", 1, 1, "For 2030 · https://shop.example/bourg"), ("cuvee", 2, 1, "150cl")]


def test_an_empty_wishlist_makes_no_list(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'e.db'}")
    migrate.upgrade(engine)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM lists")).scalar() == 0
