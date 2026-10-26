"""WineLib database models (SQLAlchemy). The single source of truth for the schema."""
from sqlalchemy import (Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Index, UniqueConstraint,
                        event, inspect)
from sqlalchemy.orm import Session, relationship, declarative_base

Base = declarative_base()

class Region(Base):
    __tablename__ = 'regions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    country = Column(String)
    color = Column(String)
    iso_code = Column(String(2))
    
    appellations = relationship("Appellation", back_populates="region_obj")
    producers = relationship("Producer", back_populates="region_obj")
    vineyards = relationship("Vineyard", back_populates="region_obj")
    wines = relationship("Wine", back_populates="region_obj")


class Appellation(Base):
    __tablename__ = 'appellations'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    region_id = Column(Integer, ForeignKey('regions.id'))
    subregion = Column(String)
    type = Column(String) # AOC, PDO, IG...
    details = Column(Text)
    colors = Column(String) # List of permitted colors
    
    # Winemap Integration
    location_link = Column(String)
    geojson = Column(Text)  # a location point (map pin), not an outline
    boundary = Column(String)  # its shape in data/geo/shapes: 'inao:291', 'eu:PDO-IT-A0281' (app/api/shape_links.py)
    winemap_name = Column(String)
    aliases = Column(String)  # other names it goes by, comma separated ("Ermitage"): imports and searches match them
    
    # PDO Metadata
    pdo_id = Column(String)
    category = Column(String)
    varieties_text = Column(Text)
    max_yield_hl = Column(Float)
    max_yield_kg = Column(Integer)
    municipalities = Column(Text)
    registration_date = Column(Date)
    
    inao_id = Column(Integer, index=True)
    
    wines = relationship("Wine", back_populates="appellation")
    region_obj = relationship("Region", back_populates="appellations")

class Varietal(Base):
    __tablename__ = 'varietals'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    aliases = Column(String) # e.g. "Shiraz, Syrah"
    # From VIVC (the Vitis International Variety Catalogue), in the reference data
    color = Column(String)  # its berries: White, Red, Pink, Grey
    origin = Column(String)  # the country it comes from
    vivc = Column(Integer)  # its VIVC variety number
    parents = Column(String)  # its parents' names, comma separated ("Gouais Blanc, Pinot"); offspring: the reverse
    # Its tasting profile (from the old grape_profiles.csv: docs/reference-data.md)
    climate = Column(String)  # "Cool-Moderate"
    depth = Column(String)  # its colour depth: "Pale"
    acidity = Column(String)  # "High"
    acid_shape = Column(String)  # "Vertical"
    acid_type = Column(String)  # "Steely"
    tannin = Column(String)  # "Low-Med"
    tannin_type = Column(String)  # "Silky, velvety"
    tannin_location = Column(String)  # where it's felt: "Tongue, roof of mouth"
    aromas = Column(String)  # its primary aromas
    notes = Column(Text)  # tasting notes
    classic_regions = Column(Text)  # "Germany: Mosel, Rheingau | France : Alsace"
    
    wines = relationship("Wine", back_populates="varietal") 


class Producer(Base):
    __tablename__ = 'producers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True) # e.g. "Domaine Leflaive"
    region_id = Column(Integer, ForeignKey('regions.id'))
    subregion = Column(String) # e.g. "Puligny-Montrachet"
    village = Column(String)
    winemaker = Column(String)
    owner = Column(String)
    type = Column(String) # domaine, maison, negoce
    importers = Column(String)
    notes = Column(Text) 
    description = Column(Text)
    profile_url = Column(String)
    lists = Column(String) # e.g. "[The New French Wine]"
    website = Column(String)
    aliases = Column(String)  # other names it goes by, comma separated ("Chave, JL Chave"): imports match them
    # Relationships
    wines = relationship("Wine", back_populates="producer")
    region_obj = relationship("Region", back_populates="producers")

class Vineyard(Base):
    __tablename__ = 'vineyards'
    __table_args__ = (Index('idx_vineyard_name_region', 'name', 'region_id'),)
    # Names aren't unique: two regions can have a vineyard of the same name
    id = Column(Integer, primary_key=True)
    vineyard_id = Column(Integer, index=True)
    name = Column(String, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'))
    sub_region = Column(String)
    village = Column(String)
    geojson = Column(Text)
    boundary = Column(String)  # its shape in data/geo/shapes: 'vineyard:bourgogne:1282' (app/api/shape_links.py)
    
    wines = relationship("Wine", back_populates="vineyard")
    region_obj = relationship("Region", back_populates="vineyards")

class Wine(Base):
    __tablename__ = 'wines'
    __table_args__ = (Index('idx_wine_lookup', 'producer_id', 'cuvee', 'appellation_id', 'varietal_id'),)
    
    id = Column(Integer, primary_key=True)
    producer_id = Column(Integer, ForeignKey('producers.id'))
    vineyard_id = Column(Integer, ForeignKey('vineyards.id'))
    
    cuvee = Column(String) # e.g. "Les Pucelles" (Raw)
    vintage = Column(String) # "2010" or "NV"
    disgorgement_date = Column(String) # e.g. "Oct 2024"
    type = Column(String)  # Red, White, Rose, Bubbles, Bubbles Rose, Sweet, Orange, Fortified
    region_id = Column(Integer, ForeignKey('regions.id'))
    appellation_id = Column(Integer, ForeignKey('appellations.id'))
    varietal_id = Column(Integer, ForeignKey('varietals.id'))
    appellation = relationship("Appellation", back_populates="wines")
    varietal = relationship("Varietal", back_populates="wines")
    vineyard = relationship("Vineyard", back_populates="wines")
    region_obj = relationship("Region", back_populates="wines")
    blend = Column(String)  # its style, one of tasks.blends.BLEND_STYLES ("Bordeaux blend", "Field blend")
    # Its grapes in order, the first the main one (varietal_id is kept equal to it: see sync_grapes)
    grapes = relationship("WineGrape", back_populates="wine", order_by="WineGrape.position",
                          cascade="all, delete-orphan", lazy="selectin")
    lwin = Column(String, index=True) # Liv-ex Wine Identification Number (LWIN7)
    drink_window_start = Column(Integer)
    drink_window_end = Column(Integer)
    # Relationships
    producer = relationship("Producer", back_populates="wines")
    inventory = relationship("Bottle", back_populates="wine")
    # Critics' scores, one per critic (loaded with the wine: pages and lists show them)
    scores = relationship("CriticScore", back_populates="wine", cascade="all, delete-orphan", lazy="selectin")

    def set_grapes(self, grapes):
        """Its grapes from [(Varietal, share or None)] in order: rows kept where the grape stays (the unique pair is
        never inserted twice), the others removed; the main grape follows."""
        by_id = {g.varietal_id: g for g in self.grapes if g.varietal_id is not None}
        rows, seen = [], set()
        for varietal, share in grapes:
            key = varietal.id if varietal.id is not None else id(varietal)
            if key in seen:
                continue
            seen.add(key)
            row = by_id.get(varietal.id) if varietal.id is not None else None
            if row is None:
                row = WineGrape(varietal=varietal)
            row.share = share
            rows.append(row)
        for i, row in enumerate(rows, 1):
            row.position = i
        self.grapes = rows
        self.varietal = rows[0].varietal if rows else None

    def sync_grapes(self):
        """The main grape (varietal) and the first of its grapes kept one: code that sets only the main grape
        (imports, older scripts) gets it as the first grape, the old first one replaced; a new list sets the main
        grape. Run before every flush."""
        state = inspect(self)
        if state.attrs.grapes.history.has_changes():
            first = self.grapes[0] if self.grapes else None
            if first is None:
                self.varietal = None
            elif first.varietal is not None:
                self.varietal = first.varietal
            else:
                self.varietal_id = first.varietal_id
            return
        object_changed = state.attrs.varietal.history.has_changes()
        id_changed = state.attrs.varietal_id.history.has_changes()
        if not object_changed and not id_changed:
            return
        if id_changed and not object_changed:  # set by id (an import): the loaded object is the old one
            main, main_id = None, self.varietal_id
        else:
            main = self.varietal
            main_id = main.id if main is not None else self.varietal_id

        def is_main(g):
            return (main is not None and g.varietal is main) or (main_id is not None and g.varietal_id == main_id)

        if main is None and main_id is None:
            self.grapes = self.grapes[1:]  # the main grape taken away
        elif self.grapes and is_main(self.grapes[0]):
            return
        else:
            kept = next((g for g in self.grapes if is_main(g)), None)
            others = [g for g in self.grapes[1:] if not is_main(g)]
            first = kept or (WineGrape(varietal=main) if main is not None else WineGrape(varietal_id=main_id))
            self.grapes = [first, *others]
        for i, g in enumerate(self.grapes, 1):
            g.position = i

    def score_of(self, critic):
        """The critic's line (case aside), or None."""
        return next((s for s in self.scores if s.critic.lower() == (critic or "").strip().lower()), None)

    def set_score(self, critic, score=None, note=None, url=None, date=None):
        """Saves a critic's score, note, link and date: its line, added or replaced (Add a score, the imports, the
        plug-ins). The line."""
        s = self.score_of(critic)
        if s is None:
            s = CriticScore(critic=" ".join(critic.split()))
            self.scores.append(s)
        s.score, s.note, s.url, s.date = score or None, note or None, url or None, date
        return s



def has_score(line):
    """A critic's line with a score ("-": searched, none found)."""
    return line is not None and (line.score or "").strip() not in ("", "-", "0", "None")


class WineGrape(Base):
    """One of a wine's grapes: its place in the wine (1 = the main grape) and its share, when known."""
    __tablename__ = "wine_grapes"
    __table_args__ = (UniqueConstraint("wine_id", "varietal_id", name="uq_wine_grapes_wine_varietal"),)

    id = Column(Integer, primary_key=True)
    wine_id = Column(Integer, ForeignKey("wines.id", ondelete="CASCADE"), nullable=False, index=True)
    varietal_id = Column(Integer, ForeignKey("varietals.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=1)
    share = Column(Float)  # percent
    wine = relationship("Wine", back_populates="grapes")
    varietal = relationship("Varietal", lazy="joined")


@event.listens_for(Session, "before_flush")
def _sync_main_grapes(session, flush_context, instances):
    for obj in [*session.new, *session.dirty]:
        if isinstance(obj, Wine):
            obj.sync_grapes()


class CriticScore(Base):
    """A critic's score for a wine: by hand (Add a score), imported (Import critic scores) or from a plug-in."""
    __tablename__ = 'critic_scores'
    __table_args__ = (UniqueConstraint('wine_id', 'critic', name='uq_critic_scores_wine_critic'),)
    id = Column(Integer, primary_key=True)
    wine_id = Column(Integer, ForeignKey('wines.id', ondelete='CASCADE'), nullable=False, index=True)
    critic = Column(String, nullable=False)  # "Robert Parker", "Vinous"...
    score = Column(String)  # as published: "95", "95+", "(95-97)"; "-" when searched and none found
    note = Column(Text)
    url = Column(String)
    date = Column(Date)  # when the review was published, when known
    wine = relationship("Wine", back_populates="scores")

class Bottle(Base):
    """Represents physical inventory"""
    __tablename__ = 'cellar'
    
    id = Column(Integer, primary_key=True)
    wine_id = Column(Integer, ForeignKey('wines.id'))
    location = Column(String) # e.g. "Rack A-12", "Offsite"
    bottle_size = Column(String, default="75cl")
    qty = Column(Integer, default=1)
    purchase_date = Column(Date)
    price = Column(Float)
    currency = Column(String, default="EUR")
    vendor = Column(String)
    provenance = Column(String) # either importer / seller / restaurant name / person who brought the wine
    last_price = Column(Float)  # last known market price
    last_price_date = Column(Date)  # date of last price check
    last_price_source = Column(String)  # where it came from: Bordeaux Index, WineLabs.ai
    wine = relationship("Wine", back_populates="inventory")
    tastings = relationship("TastingNote", back_populates="bottle")

class TastingNote(Base):
    """Your personal log"""
    __tablename__ = 'tasting_notes'
    
    id = Column(Integer, primary_key=True)
    bottle_id = Column(Integer, ForeignKey('cellar.id'), nullable=False)
    date = Column(Date)
    rating = Column(Integer) # Your 100pt score
    notes = Column(Text)     # "Explosive nose of..."
    tags = Column(String)    # "Dinner, Gift, corked"
    location = Column(String) ## will be set to place name automatically.
    sequence = Column(Integer) # Sequence in the tasting day (Seq)
    glasses = Column(Float)    # Amount drank in glasses (Gls)
    # Relationships
    bottle = relationship("Bottle", back_populates="tastings")
    place_id = Column(Integer, ForeignKey('places.id'))
    place = relationship("Place", back_populates="tastings")

class Place(Base):
    __tablename__ = 'places'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True) # e.g. "Home", a restaurant's name
    
    city = Column(String)
    country = Column(String)
    type = Column(String) # Restaurant, Home, Bar, etc.
    michelin_stars = Column(Integer)
    notes = Column(Text)
    lat = Column(Float)
    lng = Column(Float)
    
    tastings = relationship("TastingNote", back_populates="place")
    visits = relationship("RestaurantVisit", back_populates="place")

class RestaurantVisit(Base):
    __tablename__ = 'restaurants_visits'
    
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    place_id = Column(Integer, ForeignKey('places.id'))
    notes = Column(Text)
    
    place = relationship("Place", back_populates="visits")


class CustomShape(Base):
    """An outline drawn or imported in the app for one appellation or vineyard, which links to it as
    boundary = 'custom:<id>' (user data, unlike the shape store's official outlines)."""
    __tablename__ = 'custom_shapes'
    id = Column(Integer, primary_key=True)
    kind = Column(String, nullable=False)  # appellation / vineyard
    name = Column(String)  # the row's name when it was saved
    geometry = Column(Text, nullable=False)  # GeoJSON (Polygon / MultiPolygon), lon/lat, as drawn
    display = Column(Text, nullable=False)  # GeoJSON, simplified like the store's display outlines
    bbox = Column(String, nullable=False)  # "west,south,east,north"
    replaces = Column(String)  # the row's boundary before (an official shape): restored when this one is deleted
    updated = Column(DateTime, nullable=False)


class ReferenceKey(Base):
    """A reference row this installation has received (app/api/reference.py): its table and stable key (a region's
    name, an appellation's name and country...). An update only adds rows whose key was never received, so a row
    deleted or renamed here doesn't come back."""
    __tablename__ = 'reference_keys'
    id = Column(Integer, primary_key=True)
    table_name = Column(String, nullable=False)
    key = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('table_name', 'key', name='uq_reference_keys_table_key'),)
