"""Grape families, from varietals.parents (VIVC's parents, by name: scripts/reference/grapes.py): a grape's
parents and grandparents, and its offspring (the grapes naming it as a parent)."""
from reference import norm as _key  # a name as a key, the reference data's way


VIVC_PAGE = "https://www.vivc.de/index.php?r=passport%2Fview&id={}"




def parents_of(text):
    return [p.strip() for p in (text or "").split(",") if p.strip()]


class Families:
    """Every grape's parents and offspring, read once per request."""

    def __init__(self, rows):
        # rows: (id, name, aliases, parents)
        self.by_key, self.parents, self.names = {}, {}, {}
        for gid, name, aliases, parents in rows:
            self.names[gid] = name
            self.parents[gid] = parents_of(parents)
            for n in [name, *(aliases or "").split(",")]:
                if n.strip():
                    self.by_key.setdefault(_key(n), gid)
        self.offspring = {}
        for gid, ps in self.parents.items():
            for p in ps:
                pid = self.by_key.get(_key(p))
                if pid is not None:
                    self.offspring.setdefault(pid, []).append(gid)

    def node(self, name):
        """{"name", "id"}: a grape by name, its id when it's in the list."""
        gid = self.by_key.get(_key(name))
        return {"name": self.names.get(gid, name), "id": gid}

    def family(self, gid):
        """{"parents": [{"name", "id", "parents": [nodes]}], "offspring": [nodes]}"""
        parents = []
        for p in self.parents.get(gid, []):
            n = self.node(p)
            n["parents"] = [self.node(gp) for gp in self.parents.get(n["id"], [])] if n["id"] is not None else []
            parents.append(n)
        offspring = sorted((self.node(self.names[o]) for o in self.offspring.get(gid, [])), key=lambda n: n["name"].lower())
        return {"parents": parents, "offspring": offspring}


def families(session):
    from db import Varietal
    return Families(session.query(Varietal.id, Varietal.name, Varietal.aliases, Varietal.parents).all())
